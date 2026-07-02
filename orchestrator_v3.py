"""orchestrator_v3 - pure-Python GoPay long-link generator.

完全去除 BitBrowser/CDP/浏览器依赖。复用 stripe.js v3 反爬已破解的 fingerprint
重放链路（见 stripe_reverse/_gopay_pure_python.py 实测验证）。

链路（8 步）:
  1. chatgpt /backend-api/payments/checkout (JP exit) -> cs_live
  2. stripe /v1/payment_pages/{cs}/init -> init_checksum + config_id + hosted_url
  3. stripe POST /v1/payment_methods (gopay, IDR billing) -> fresh pm
  4. stripe POST /v1/payment_pages/{cs}/confirm (REPLAY confirm_body.txt
     fingerprint) -> submission_attempt requires_approval
  5. chatgpt /backend-api/payments/checkout/approve (JP exit) -> approved
  6. GET /v1/payment_pages/{cs} 带 beta flags (custom_checkout_server_updates_1
     + custom_checkout_manual_approval_1) -> 物化的 payment_intent
  7. 若 cs 未物化 intent，2nd /confirm via ID 出口代理兜底
  8. GET /v1/payment_intents/{pi}?key=&client_secret= ->
     next_action.redirect_to_url.url -> pm-redirects.stripe.com -> follow ->
     app.midtrans.com/snap/v4/redirection/{uuid}

CLI: `python app/orchestrator_v3.py`
输出: run-output/gopay_midtrans_url.txt
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse as up
import uuid as _uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parent
RUN_DIR = WORKSPACE_ROOT / "run-output"
sys.path.insert(0, str(ROOT))
import app  # noqa: E402
import stripe_fingerprint  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


CONFIRM_BODY_PATH = ROOT / "data" / "confirm_body.txt"
TOKEN_PATH = ROOT / "access_token.txt"
OUTPUT_URL_PATH = RUN_DIR / "gopay_midtrans_url.txt"
RUN_LOG_PATH = RUN_DIR / "orchestrator_v3_run.log"
INTENT_DUMP_PATH = RUN_DIR / "intent_get_response.json"
CS_DUMP_PATH = RUN_DIR / "cs_after_approve.json"
FIRST_CONFIRM_DUMP_PATH = RUN_DIR / "first_confirm_response.json"

_log_lines: list[str] = []


def log(msg: str = "") -> None:
    print(msg)
    _log_lines.append(msg)


def short(v, n: int = 80) -> str:
    s = str(v or "")
    return s if len(s) <= n else s[:n] + "..."


def make_id_session(req):
    """印尼出口 stripe session（GoPay 相关 stripe 调用必须 ID 出口）。"""
    proxy = (
        os.getenv("OPENAI_PAY_GOPAY_PROVIDER_PROXY", "").strip()
        or os.getenv("OPENAI_PAY_DEFAULT_PROXY", "").strip()
        or str(getattr(req, "proxy", "") or "").strip()
    )
    if not proxy:
        raise RuntimeError("GoPay 二次 confirm 需要 ID 出口代理，请设置 OPENAI_PAY_GOPAY_PROVIDER_PROXY。")
    return app.build_stripe_session(req, proxy_override=proxy), proxy

def main() -> int:
    t0 = time.time()
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    # 加载 fingerprint 抓包
    try:
        capture = stripe_fingerprint.load_capture("gopay", CONFIRM_BODY_PATH)
    except stripe_fingerprint.FingerprintNotFound as exc:
        log(f"ABORT: {exc}")
        return 1
    cap_body_text = CONFIRM_BODY_PATH.read_text(encoding="utf-8").strip()
    log("== fingerprint replay fields (from confirm_body.txt) ==")
    for k in ("js_checksum", "rv_timestamp", "version", "_stripe_version"):
        log(f"  [REUSE] {k} = {short(capture.get(k), 90)}")

    # 构造 LongLinkRequest（默认 JP 出口）
    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    req = app.LongLinkRequest(accessToken=token, link_type="gopay", billing_country="ID")
    app.prepare_request_proxy(req)
    log(f"\nJP proxy: {short(req.proxy, 90)}")

    chatgpt = app.build_chatgpt_session(req)
    billing = app.billing_for_link_type("gopay", app.account_email_from_token(token))
    log(f"billing: name={billing.get('name')} email={billing.get('email')} country={billing.get('country')}")

    # ====================================================================
    # STEP 1: chatgpt /backend-api/payments/checkout (IDR / GoPay)
    # ====================================================================
    log("\n== step1: chatgpt /backend-api/payments/checkout ==")
    t1 = time.time()
    checkout_body = {
        "entry_point": "all_plans_pricing_modal",
        "plan_name": "chatgptgoplan",
        "billing_details": {"country": "ID", "currency": "IDR"},
        "promo_campaign": {
            "promo_campaign_id": "go-1-month-free",
            "is_coupon_from_query_param": False,
        },
        "checkout_ui_mode": "hosted",
    }
    cr = chatgpt.post(
        "https://chatgpt.com/backend-api/payments/checkout",
        json=checkout_body,
        headers={
            "Referer": "https://chatgpt.com/",
            "x-openai-target-path": "/backend-api/payments/checkout",
            "x-openai-target-route": "/backend-api/payments/checkout",
        },
        timeout=30,
    )
    log(f"http: {cr.status_code} ({time.time()-t1:.1f}s)")
    try:
        cj = cr.json()
    except Exception:
        log(f"raw: {cr.text[:300]}")
        return 1
    cs_id = cj.get("checkout_session_id") or ""
    processor_entity = app.extract_processor_entity(cj) or "openai_llc"
    log(f"cs_id: {cs_id}")
    log(f"processor_entity: {processor_entity}")
    if not cs_id.startswith("cs_"):
        log(f"ABORT step1: no cs_id; resp={short(cj, 300)}")
        return 1

    # ====================================================================
    # STEP 2: stripe init -> init_checksum + config_id + hosted_url
    # ====================================================================
    log("\n== step2: stripe /v1/payment_pages/{cs}/init ==")
    t2 = time.time()
    try:
        init = app.stripe_init(cs_id, req)
    except Exception as e:
        log(f"ABORT step2: {e}")
        return 1
    log(f"http: 200 ({time.time()-t2:.1f}s)")
    due = (init.get("total_summary") or {}).get("due")
    pmts = init.get("ordered_payment_method_types")
    init_checksum = init.get("init_checksum") or ""
    config_id = init.get("config_id") or ""
    stripe_hosted_url = init.get("stripe_hosted_url") or ""
    log(f"due={due} pmts={pmts}")
    log(f"init_checksum: {init_checksum}")
    log(f"config_id: {config_id}")
    log(f"stripe_hosted_url has #fid: {'#' in stripe_hosted_url}")

    fid_fragment = ""
    if "#" in stripe_hosted_url:
        fid_fragment = stripe_hosted_url.split("#", 1)[1]
    if not fid_fragment:
        cap_ru = up.unquote(capture.get("return_url", ""))
        if "#" in cap_ru:
            fid_fragment = cap_ru.split("#", 1)[1]
    return_url = (
        f"https://pay.openai.com/c/pay/{cs_id}?redirect_pm_type=gopay"
        f"&lid=00000000-0000-0000-0000-000000000000&ui_mode=custom"
    )
    if fid_fragment:
        return_url += "#" + fid_fragment

    # ====================================================================
    # STEP 3: stripe POST /v1/payment_methods (gopay, IDR billing)
    # ====================================================================
    log("\n== step3: stripe POST /v1/payment_methods (gopay) ==")
    t3 = time.time()
    stripe_pk = app.DEFAULT_STRIPE_PK
    stripe_sess = app.build_stripe_session(req)  # JP exit ok for /payment_methods
    try:
        pm_id = app.stripe_create_payment_method(
            stripe_sess, cs_id, stripe_pk, billing, "gopay", {"config_id": config_id}
        )
    except Exception as e:
        log(f"  JP-exit failed: {e}; retry via ID exit (711)")
        stripe_id_sess, id_proxy = make_id_session(req)
        try:
            pm_id = app.stripe_create_payment_method(
                stripe_id_sess, cs_id, stripe_pk, billing, "gopay", {"config_id": config_id}
            )
            log(f"  ID-exit pm ok via {short(id_proxy, 90)}")
        except Exception as e2:
            log(f"ABORT step3: {e2}")
            return 1
    log(f"http: 200 ({time.time()-t3:.1f}s)")
    log(f"pm_id: {pm_id}")

    # ====================================================================
    # STEP 4: 1st confirm with fingerprint replay
    # ====================================================================
    log("\n== step4: 1st stripe POST /v1/payment_pages/{cs}/confirm (fingerprint replay) ==")
    t4 = time.time()
    orig_cs_in_cap = re.search(r"cs_live_[A-Za-z0-9]+", cap_body_text).group(0)

    def build_replay_body(pm: str, cs: str) -> str:
        pairs = up.parse_qsl(cap_body_text, keep_blank_values=True)
        rebuilt: list[tuple[str, str]] = []
        for k, v in pairs:
            nv = v.replace(orig_cs_in_cap, cs)
            if k == "client_attribution_metadata[checkout_session_id]":
                nv = cs
            if k == "client_attribution_metadata[checkout_config_id]":
                nv = config_id
            if k == "client_attribution_metadata[client_session_id]":
                nv = str(_uuid.uuid4())
            if k == "payment_method":
                nv = pm
            if k == "init_checksum":
                nv = init_checksum
            if k == "return_url":
                nv = return_url
            if k == "expected_amount":
                # IDR minor units: 75,000 IDR = 7,500,000；以 init.total_summary.due 为准
                nv = str(due or 7500000)
            if k == "key":
                nv = stripe_pk
            rebuilt.append((k, nv))
        return up.urlencode(rebuilt)

    body_enc = build_replay_body(pm_id, cs_id)
    log(f"body bytes: {len(body_enc)}")

    confirm_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Referer": "https://pay.openai.com/",
        "Origin": "https://pay.openai.com",
        "User-Agent": app.DEFAULT_USER_AGENT,
    }
    rr = stripe_sess.post(
        f"https://api.stripe.com/v1/payment_pages/{cs_id}/confirm",
        data=body_enc,
        headers=confirm_headers,
        timeout=30,
    )
    log(f"http: {rr.status_code} ({time.time()-t4:.1f}s)")
    try:
        rj1 = rr.json()
    except Exception:
        rj1 = {"_raw": rr.text}
    FIRST_CONFIRM_DUMP_PATH.write_text(
        json.dumps(rj1, ensure_ascii=False, indent=2)[:200_000], encoding="utf-8"
    )
    sub = rj1.get("submission_attempt") or {}
    err1 = rj1.get("error") or {}
    log(f"  object={rj1.get('object')} status={rj1.get('status')}")
    log(f"  submission_attempt: id={sub.get('id')} state={sub.get('state')}")
    log(f"  approval_method: {rj1.get('approval_method')}")
    if err1:
        log(f"  error: code={err1.get('code')} msg={short(err1.get('message'), 200)}")
    if rr.status_code != 200:
        log("ABORT step4: first confirm not 200")
        return 1
    attempt_id = sub.get("id") or ""
    if not attempt_id:
        log("ABORT step4: no submission_attempt.id (fingerprint replay rejected?)")
        return 1

    # ====================================================================
    # STEP 5: chatgpt approve -> approved
    # ====================================================================
    log("\n== step5: chatgpt /backend-api/payments/checkout/approve ==")
    t5 = time.time()
    approve_body = {"checkout_session_id": cs_id, "processor_entity": processor_entity}
    approved = False
    approve_resp = {}
    for attempt in range(1, 7):
        try:
            chatgpt.post(
                "https://chatgpt.com/backend-api/sentinel/ping",
                json={},
                headers={
                    "Referer": "https://chatgpt.com/",
                    "x-openai-target-path": "/backend-api/sentinel/ping",
                    "x-openai-target-route": "/backend-api/sentinel/ping",
                },
                timeout=15,
            )
        except Exception:
            pass
        ar = chatgpt.post(
            "https://chatgpt.com/backend-api/payments/checkout/approve",
            json=approve_body,
            headers={
                "Referer": f"https://chatgpt.com/checkout/{processor_entity}/{cs_id}",
                "x-openai-target-path": "/backend-api/payments/checkout/approve",
                "x-openai-target-route": "/backend-api/payments/checkout/approve",
            },
            timeout=30,
        )
        try:
            arj = ar.json()
        except Exception:
            arj = {"_raw": ar.text[:200]}
        result = (arj.get("result") or "").lower()
        log(f"  attempt {attempt}: http={ar.status_code} result={result!r}")
        approve_resp = arj
        if result == "approved":
            approved = True
            break
        time.sleep(2.0)
    log(f"approve total: {time.time()-t5:.1f}s, approved={approved}")
    if not approved:
        log(f"ABORT step5: approve never returned approved; last: {short(approve_resp, 300)}")
        return 1

    # ====================================================================
    # STEP 6: GET cs WITH BETA FLAGS to materialize payment_intent
    # 不带 beta flags 时 stripe 返回精简 cs，藏起 payment_intent。
    # ====================================================================
    log("\n== step6: poll GET /v1/payment_pages/{cs} WITH beta flags for materialized intent ==")
    t6 = time.time()
    time.sleep(5)  # 给 stripe 时间消化 approve
    BETA_GET_PARAMS = {
        "elements_session_client[client_betas][0]": "custom_checkout_server_updates_1",
        "elements_session_client[client_betas][1]": "custom_checkout_manual_approval_1",
        "elements_session_client[elements_init_source]": "custom_checkout",
        "elements_session_client[referrer_host]": "chatgpt.com",
        "elements_session_client[session_id]": f"elements_session_{_uuid.uuid4().hex[:11]}",
        "elements_session_client[stripe_js_id]": str(_uuid.uuid4()),
        "elements_session_client[locale]": "en-US",
        "elements_session_client[is_aggregation_expected]": "false",
        "elements_options_client[saved_payment_method][enable_save]": "never",
        "elements_options_client[saved_payment_method][enable_redisplay]": "never",
        "key": stripe_pk,
        "_stripe_version": "2025-03-31.basil; checkout_server_update_beta=v1; checkout_manual_approval_preview=v1",
    }
    advanced = False
    last_state = ""
    cs_payload_final: dict = {}
    pi_on_cs = None
    si_on_cs = None
    for poll_i in range(1, 25):  # ~50s
        try:
            pr = stripe_sess.get(
                f"https://api.stripe.com/v1/payment_pages/{cs_id}",
                params=BETA_GET_PARAMS,
                timeout=15,
            )
        except Exception as e:
            log(f"  poll {poll_i}: EXC {short(e, 120)}")
            time.sleep(2.0)
            continue
        if pr.status_code != 200:
            log(f"  poll {poll_i}: http={pr.status_code} {short(pr.text, 200)}")
            time.sleep(2.0)
            continue
        try:
            pj = pr.json()
        except Exception:
            time.sleep(2.0)
            continue
        cs_payload_final = pj
        sub_now = pj.get("submission_attempt") or {}
        state_now = sub_now.get("state") or ""
        pi_on_cs = pj.get("payment_intent")
        si_on_cs = pj.get("setup_intent")
        if state_now != last_state or pi_on_cs or si_on_cs or poll_i == 1:
            log(f"  poll {poll_i} (+{time.time()-t6:.1f}s): state={state_now!r} pi={bool(pi_on_cs)} si={bool(si_on_cs)}")
            last_state = state_now
        if pi_on_cs or si_on_cs:
            advanced = True
            log(f"  ✓ intent materialized on cs after {time.time()-t6:.1f}s")
            break
        if app.extract_redirect_to_url(pj):
            log("  ✓ redirect found on cs (no intent)")
            advanced = True
            break
        time.sleep(2.0)
    log(f"  advanced={advanced} after {time.time()-t6:.1f}s, last_state={last_state!r}")
    if cs_payload_final:
        CS_DUMP_PATH.write_text(
            json.dumps(cs_payload_final, ensure_ascii=False, indent=2)[:200_000],
            encoding="utf-8",
        )

    # ====================================================================
    # STEP 7: 优先用 cs 物化的 intent；否则 ID 出口 2nd /confirm 兜底
    # ====================================================================
    log("\n== step7: extract intent ==")
    pi = pi_on_cs
    si = si_on_cs
    intent = pi or si
    intent_kind = "payment_intent" if pi else ("setup_intent" if si else "none")
    used_id_exit = False
    stripe_for_get = stripe_sess

    if intent:
        log(f"  using cs-embedded intent: kind={intent_kind} id={intent.get('id')}")
    else:
        log("  no intent on cs; fallback to ID-exit 2nd /confirm")
        stripe_id_sess, id_proxy = make_id_session(req)
        fresh_pm_id = None
        for attempt in range(1, 5):
            try:
                fresh_pm_id = app.stripe_create_payment_method(
                    stripe_id_sess, cs_id, stripe_pk, billing, "gopay", {"config_id": config_id}
                )
                log(f"  fresh ID-exit pm: {fresh_pm_id}")
                break
            except Exception as e:
                log(f"  pm attempt {attempt} fail: {short(e, 120)}; new ID sid")
                stripe_id_sess, id_proxy = make_id_session(req)
                time.sleep(1)
        if not fresh_pm_id:
            log("ABORT step7: could not create GoPay pm via ID exit")
            return 1
        body2 = build_replay_body(fresh_pm_id, cs_id)
        rr2 = stripe_id_sess.post(
            f"https://api.stripe.com/v1/payment_pages/{cs_id}/confirm",
            data=body2,
            headers=confirm_headers,
            timeout=30,
        )
        log(f"  2nd confirm via ID exit http: {rr2.status_code}")
        try:
            rj2 = rr2.json()
        except Exception:
            rj2 = {"_raw": rr2.text[:300]}
        pi = rj2.get("payment_intent")
        si = rj2.get("setup_intent")
        intent = pi or si
        intent_kind = "payment_intent" if pi else ("setup_intent" if si else "none")
        used_id_exit = True
        stripe_for_get = stripe_id_sess

        if not intent:
            # 再尝试一轮 beta 轮询
            log("  retry: poll cs via ID exit + beta flags after 2nd confirm")
            time.sleep(3)
            for poll_i in range(1, 10):
                pr = stripe_id_sess.get(
                    f"https://api.stripe.com/v1/payment_pages/{cs_id}",
                    params=BETA_GET_PARAMS,
                    timeout=15,
                )
                if pr.status_code == 200:
                    pj = pr.json()
                    if pj.get("payment_intent") or pj.get("setup_intent"):
                        pi = pj.get("payment_intent")
                        si = pj.get("setup_intent")
                        intent = pi or si
                        intent_kind = "payment_intent" if pi else "setup_intent"
                        log(f"    ✓ intent after ID-exit beta poll {poll_i}: {intent.get('id')}")
                        break
                time.sleep(2)

    if not intent:
        log("ABORT step7: no payment_intent/setup_intent")
        return 1

    intent_id = intent.get("id") or ""
    client_secret = intent.get("client_secret") or ""
    log(f"  intent kind: {intent_kind}")
    log(f"  intent id: {intent_id}")
    log(f"  client_secret: {short(client_secret, 60)}")
    log(f"  status: {intent.get('status')}")

    # ====================================================================
    # STEP 8: GET intent -> next_action.redirect_to_url.url -> midtrans
    # ====================================================================
    log("\n== step8: GET intent + follow pm-redirects -> midtrans ==")
    intent_path = "payment_intents" if pi else "setup_intents"
    t8 = time.time()
    gr = stripe_for_get.get(
        f"https://api.stripe.com/v1/{intent_path}/{intent_id}",
        params={"key": stripe_pk, "client_secret": client_secret},
        timeout=20,
    )
    log(f"  GET {intent_path} http: {gr.status_code} ({time.time()-t8:.1f}s)")
    try:
        gj = gr.json()
    except Exception:
        gj = {"_raw": gr.text[:300]}
    INTENT_DUMP_PATH.write_text(
        json.dumps(gj, ensure_ascii=False, indent=2)[:300_000], encoding="utf-8"
    )
    log(f"  status: {gj.get('status')}")
    nxt2 = gj.get("next_action") or {}
    log(f"  next_action.type: {nxt2.get('type')}")
    redir = app.extract_redirect_to_url(gj)
    log(f"  redirect_to_url: {short(redir, 200)}")

    midtrans_url = ""
    if redir:
        log("  [follow pm-redirects -> midtrans]")
        try:
            fr = stripe_for_get.get(
                redir,
                allow_redirects=True,
                timeout=20,
                headers={
                    "User-Agent": app.DEFAULT_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            log(f"    final_url={short(fr.url, 200)} (chain={len(fr.history)} hops)")
            if "midtrans" in fr.url:
                midtrans_url = fr.url.split("#", 1)[0]
            else:
                body_text = fr.text[:4000] if fr.text else ""
                m = re.search(
                    r"https?://app\.midtrans\.com/snap/v[0-9]+/redirection/[A-Za-z0-9\-]+",
                    body_text,
                )
                if m:
                    midtrans_url = m.group(0)
                    log(f"    midtrans from body: {midtrans_url}")
                else:
                    m2 = re.search(r"https?://app\.midtrans\.com[^\"'<>\s]+", body_text)
                    if m2:
                        midtrans_url = m2.group(0)
                        log(f"    midtrans (loose) from body: {midtrans_url}")
        except Exception as e:
            log(f"    follow EXC: {short(e, 200)}")

    # ====================================================================
    # 最终输出
    # ====================================================================
    log("\n== RESULT ==")
    log(f"  cs_id:        {cs_id}")
    log(f"  pm_id:        {pm_id}")
    log(f"  intent_id:    {intent_id} ({intent_kind})")
    log(f"  used_id_exit: {used_id_exit}")
    log(f"  stripe_redir: {short(redir, 200)}")
    log(f"  midtrans_url: {midtrans_url or '(NOT RESOLVED)'}")
    log(f"\nTOTAL: {time.time()-t0:.1f}s")

    if midtrans_url:
        OUTPUT_URL_PATH.write_text(midtrans_url, encoding="utf-8")
        log(f"\nWROTE: {OUTPUT_URL_PATH}")
        log(f"MIDTRANS URL: {midtrans_url}")
        return 0
    elif redir:
        log("\nstripe pm-redirects URL captured, but midtrans not resolved")
        return 4
    else:
        log("\nno redirect URL from final GET")
        return 5


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    except Exception as e:
        import traceback
        log(f"\nUNCAUGHT: {e}\n{traceback.format_exc()}")
        rc = 99
    finally:
        try:
            RUN_LOG_PATH.write_text("\n".join(_log_lines), encoding="utf-8")
        except Exception:
            pass
    sys.exit(rc)
