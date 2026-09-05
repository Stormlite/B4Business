"""scripts/notify.py — WhatsApp alerts for high-confidence daily picks via Twilio

Sends TWO separate messages each run:
  1. High-confidence Over 2.5 picks (the original message)
  2. Low-scoring watch — confident Under 2.5 picks

Each is built and sent independently, so one failing doesn't block the other.
"""
import sys, os, time, json
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predict import score_todays_fixtures


def _build_message_body(picks: pd.DataFrame, label: str, marker: str, source_branch: str) -> str:
    msg_body = f"{marker} *B4Business {label}* {marker}\n\n"
    for _, row in picks.iterrows():
        o25  = row["over_2_5_probability"] * 100
        o05  = row.get("over_0_5_probability", float("nan")) * 100
        btts = row.get("btts_probability", 0) * 100
        time_= row.get("match_time", "")
        msg_body += f"{marker} *{row['home_team']} vs {row['away_team']}*"
        if time_: msg_body += f"  ⏰ {time_}"
        msg_body += f"\n   Over 2.5: *{o25:.1f}%*"
        if o05 == o05:  # NaN-safe check — only show if the Over 0.5 model produced a value
            msg_body += f"  ·  Over 0.5: *{o05:.1f}%*"
        msg_body += f"  ·  BTTS: *{btts:.1f}%*\n\n"
    msg_body += f"_Automated forecast · B4Business ML pipeline ({source_branch})_"
    return msg_body


def _send_picks_message(client, picks: pd.DataFrame, label: str, marker: str,
                         target_num: str, custom_content_sid: str, sandbox_template_sid: str,
                         source_branch: str):
    from twilio.base.exceptions import TwilioRestException

    if picks.empty:
        print(f"ℹ️  No picks for '{label}' today. No message will be sent for this section.")
        return

    print(f"{marker} {len(picks)} pick(s) found for '{label}'. Building message...")
    msg_body = _build_message_body(picks, label, marker, source_branch)

    # Three possible delivery modes, tried in this priority order:
    #   1. TWILIO_CUSTOM_CONTENT_SID — a custom, freely-worded template with
    #      ONE variable ({{1}} = the whole digest).
    #   2. TWILIO_SANDBOX_TEMPLATE_SID — the Sandbox's built-in "Order
    #      Notifications" template (4 fixed variables), repurposed to carry
    #      picks data.
    #   3. Free-form Body message (no template) — default when neither SID
    #      is set. Only works inside a live 24h session.
    #
    # NOTE on the two template modes: an approved WhatsApp template's fixed
    # wording can't change per-call — only the *content* of its variables
    # can. So "Low-Scoring Watch" can't relabel the template's own fixed
    # text ("Our model found {{2}} high-confidence selection(s)...", "Your
    # {{1}} order...") — it's tagged into an existing variable instead
    # (the date/brand variable) rather than creating a second approved
    # template. Free-form mode has no such constraint.
    try:
        if custom_content_sid:
            print(f"📨 [{label}] Sending via custom template (TWILIO_CUSTOM_CONTENT_SID)...")
            today_str = pd.Timestamp.now().strftime("%d %B %Y") + f" ({source_branch})"
            tagged_date = f"{marker} {label} — {today_str}" if label != "Daily Picks" else today_str
            pick_lines = []
            for _, row in picks.iterrows():
                o25 = row["over_2_5_probability"] * 100
                pick_lines.append(f"{row['home_team']} vs {row['away_team']}: Over 2.5 {o25:.0f}%")

            slots = pick_lines[:3] + ["—"] * max(0, 3 - len(pick_lines))
            if len(pick_lines) > 3:
                slots[2] = f"{pick_lines[2]} (+{len(pick_lines) - 3} more, see app)"

            message = client.messages.create(
                content_sid=custom_content_sid,
                content_variables=json.dumps({
                    "1": tagged_date,
                    "2": str(len(picks)),
                    "3": slots[0],
                    "4": slots[1],
                    "5": slots[2],
                }),
                from_="whatsapp:+14155238886",
                to=f"whatsapp:{target_num}",
            )
        elif sandbox_template_sid:
            print(f"📨 [{label}] Sending via Sandbox's built-in 'Order Notifications' template "
                  f"(TWILIO_SANDBOX_TEMPLATE_SID)...")
            lines = []
            for _, row in picks.iterrows():
                o25 = row["over_2_5_probability"] * 100
                lines.append(f"{row['home_team']} v {row['away_team']}: O2.5 {o25:.0f}%")
            details = " | ".join(lines)
            if len(details) > 900:
                details = details[:880] + f"...(+{len(picks) - 1} more, see app)"
            brand_tag = f"B4Business {marker} {label} ({source_branch})" if label != "Daily Picks" \
                        else f"B4Business ({source_branch})"
            message = client.messages.create(
                content_sid=sandbox_template_sid,
                content_variables=json.dumps({
                    "1": brand_tag,
                    "2": f"{len(picks)} Pick{'s' if len(picks) != 1 else ''}",
                    "3": "today",
                    "4": details,
                }),
                from_="whatsapp:+14155238886",
                to=f"whatsapp:{target_num}",
            )
        else:
            print(f"📨 [{label}] Sending free-form — requires an active 24h session. "
                  f"If this fails with 63015/63016, re-join the Sandbox on WhatsApp.")
            message = client.messages.create(
                body=msg_body,
                from_="whatsapp:+14155238886",
                to=f"whatsapp:{target_num}",
            )
    except TwilioRestException as e:
        print(f"❌ [{label}] Twilio failed to send. Error {e.code}: {e.msg}")
        if e.code == 63015:
            print("   → The target number has not joined (or has fallen out of) "
                  "the Twilio Sandbox. Re-send the 'join <code>' message on WhatsApp.")
        elif e.code == 63016:
            print("   → Outside the 24h session window and no template was used. "
                  "Either re-join the Sandbox now, or set TWILIO_SANDBOX_TEMPLATE_SID "
                  "/ TWILIO_CUSTOM_CONTENT_SID to send outside the session window.")
        raise

    print(f"✅ [{label}] WhatsApp message accepted by Twilio. SID: {message.sid} · status: {message.status}")

    time.sleep(3)
    refreshed = client.messages(message.sid).fetch()
    print(f"📬 [{label}] Delivery status after 3s: {refreshed.status}"
          + (f" (error {refreshed.error_code}: {refreshed.error_message})" if refreshed.error_code else ""))
    if refreshed.status in ("failed", "undelivered"):
        if refreshed.error_code == 63015:
            print(f"⚠️  [{label}] Sandbox opt-in has likely expired — re-join via WhatsApp.")
        elif refreshed.error_code == 63016:
            print(f"⚠️  [{label}] Outside the 24h session window and no template was used this "
                  f"run — either re-join now, or set a template SID env var.")
        else:
            print(f"⚠️  [{label}] Message was not delivered — see error code above.")


def dispatch_whatsapp_alerts():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    target_num  = os.getenv("TARGET_WHATSAPP_NUMBER")
    custom_content_sid   = os.getenv("TWILIO_CUSTOM_CONTENT_SID")
    sandbox_template_sid = os.getenv("TWILIO_SANDBOX_TEMPLATE_SID")

    if not all([account_sid, auth_token, target_num]):
        print("⚠️  Twilio credentials missing. Skipping notification.")
        return

    print("📡 Scanning for high-confidence picks...")
    df = score_todays_fixtures()

    if df is None or df.empty:
        print("ℹ️  No fixtures today.")
        return

    print(f"📊 {len(df)} fixture(s) scored today.")

    # high_conf_over / high_conf_under split the old merged high_conf_pick
    # flag into its two actual halves (that flag OR'd both directions
    # together — a confidently-under match and a confidently-over match
    # were indistinguishable in a single 'high_conf_pick' list). Falls back
    # to threshold logic directly for any older cached predictions that
    # predate the split.
    if "high_conf_over" in df.columns:
        over_picks = df[df["high_conf_over"] == True]
    elif "high_conf_pick" in df.columns:
        over_picks = df[(df["high_conf_pick"] == True) & (df["over_2_5_probability"] >= 0.5)]
    else:
        over_picks = df[df["over_2_5_probability"] >= 0.62]

    if "high_conf_under" in df.columns:
        under_picks = df[df["high_conf_under"] == True]
    elif "high_conf_pick" in df.columns:
        under_picks = df[(df["high_conf_pick"] == True) & (df["over_2_5_probability"] < 0.5)]
    else:
        under_picks = df[df["over_2_5_probability"] <= 0.38]

    if over_picks.empty and under_picks.empty:
        print("ℹ️  No high-confidence picks in either direction today "
              "(none crossed the 62%/38% thresholds). No WhatsApp messages will be sent.")
        return

    source_branch = os.getenv("GITHUB_REF_NAME", "local")

    from twilio.rest import Client
    client = Client(account_sid, auth_token)

    errors = []
    for picks, label, marker in [
        (over_picks,  "Daily Picks",       "🔥"),
        (under_picks, "Low-Scoring Watch", "🧊"),
    ]:
        try:
            _send_picks_message(client, picks, label, marker, target_num,
                                 custom_content_sid, sandbox_template_sid, source_branch)
        except Exception as e:
            errors.append(f"{label}: {e}")

    if errors:
        raise RuntimeError(f"{len(errors)} of 2 WhatsApp message(s) failed — " + "; ".join(errors))


if __name__ == "__main__":
    dispatch_whatsapp_alerts()
