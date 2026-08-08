"""scripts/notify.py — WhatsApp alerts for high-confidence daily picks via Twilio"""
import sys, os, time, json
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predict import score_todays_fixtures

def dispatch_whatsapp_alerts():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    target_num  = os.getenv("TARGET_WHATSAPP_NUMBER")

    # Three possible delivery modes, tried in this priority order:
    #   1. TWILIO_CUSTOM_CONTENT_SID — a custom, freely-worded template with
    #      ONE variable ({{1}} = the whole digest). Only works if Twilio
    #      actually allows creating+approving a custom template without a
    #      registered WhatsApp Sender — unconfirmed as of writing, worth
    #      testing via Console → Content Template Builder → create.
    #   2. TWILIO_SANDBOX_TEMPLATE_SID — the Sandbox's built-in "Order
    #      Notifications" template (4 fixed variables), repurposed to carry
    #      picks data. Confirmed working on Sandbox without a paid account.
    #   3. Free-form Body message (no template) — default when neither SID
    #      is set. Only works inside a live 24h session, i.e. you've
    #      messaged the Sandbox number (join code or otherwise) recently.
    #      Requires manually re-joining roughly every 3 days when the
    #      Sandbox opt-in lapses — accepted tradeoff for a free research
    #      project rather than upgrading Twilio.
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

    # Use the model's high_conf_pick flag (≥62% confidence) instead of a hard 75% cut
    if "high_conf_pick" in df.columns:
        picks = df[df["high_conf_pick"] == True]
    else:
        picks = df[df["over_2_5_probability"] >= 0.62]

    if picks.empty:
        print("ℹ️  No high-confidence picks today (none crossed the 62% threshold). "
              "No WhatsApp message will be sent.")
        return

    print(f"🔥 {len(picks)} high-confidence pick(s) found. Building message...")

    msg_body = "⚽ *B4Business Daily Picks* ⚽\n\n"
    for _, row in picks.iterrows():
        o25  = row["over_2_5_probability"] * 100
        o05  = row.get("over_0_5_probability", float("nan")) * 100
        btts = row.get("btts_probability", 0) * 100
        time_= row.get("match_time", "")
        msg_body += f"🔥 *{row['home_team']} vs {row['away_team']}*"
        if time_: msg_body += f"  ⏰ {time_}"
        msg_body += f"\n   Over 2.5: *{o25:.1f}%*"
        if o05 == o05:  # NaN-safe check — only show if the Over 0.5 model produced a value
            msg_body += f"  ·  Over 0.5: *{o05:.1f}%*"
        msg_body += f"  ·  BTTS: *{btts:.1f}%*\n\n"

    msg_body += "_Automated forecast · B4Business ML pipeline_"

    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException

    client = Client(account_sid, auth_token)

    try:
        if custom_content_sid:
            print("📨 Sending via custom template (TWILIO_CUSTOM_CONTENT_SID)...")
            # Matches the approved template:
            #   "⚽ B4Business Daily Picks – {{1}}
            #
            #    Our model found {{2}} high-confidence selection(s) today:
            #
            #    1️⃣ {{3}}
            #    2️⃣ {{4}}
            #    3️⃣ {{5}}
            #
            #    Automated forecast, not betting advice. View more: b4business.streamlit.app"
            # Fixed 3 pick-slots since templates can't have a variable count —
            # this covers real usage (0-3 high-confidence picks/day so far).
            # Extra picks beyond 3 get folded into slot 3 as a "+N more" note
            # rather than dropped silently; unused slots show "—".
            today_str = pd.Timestamp.now().strftime("%d %B %Y")
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
                    "1": today_str,
                    "2": str(len(picks)),
                    "3": slots[0],
                    "4": slots[1],
                    "5": slots[2],
                }),
                from_="whatsapp:+14155238886",
                to=f"whatsapp:{target_num}",
            )
        elif sandbox_template_sid:
            print("📨 Sending via Sandbox's built-in 'Order Notifications' template "
                  "(TWILIO_SANDBOX_TEMPLATE_SID)...")
            lines = []
            for _, row in picks.iterrows():
                o25 = row["over_2_5_probability"] * 100
                lines.append(f"{row['home_team']} v {row['away_team']}: O2.5 {o25:.0f}%")
            details = " | ".join(lines)
            if len(details) > 900:
                details = details[:880] + f"...(+{len(picks) - 1} more, see app)"
            message = client.messages.create(
                content_sid=sandbox_template_sid,
                content_variables=json.dumps({
                    "1": "B4Business",
                    "2": f"{len(picks)} High-Confidence Pick{'s' if len(picks) != 1 else ''}",
                    "3": "today",
                    "4": details,
                }),
                from_="whatsapp:+14155238886",
                to=f"whatsapp:{target_num}",
            )
        else:
            print("📨 Sending free-form (Option 3) — requires an active 24h session. "
                  "If this fails with 63015/63016, re-join the Sandbox on WhatsApp.")
            message = client.messages.create(
                body=msg_body,
                from_="whatsapp:+14155238886",
                to=f"whatsapp:{target_num}",
            )
    except TwilioRestException as e:
        print(f"❌ Twilio failed to send the WhatsApp message. Error {e.code}: {e.msg}")
        if e.code == 63015:
            print("   → The target number has not joined (or has fallen out of) "
                  "the Twilio Sandbox. Re-send the 'join <code>' message on WhatsApp.")
        elif e.code == 63016:
            print("   → Outside the 24h session window and no template was used. "
                  "Either re-join the Sandbox now, or set TWILIO_SANDBOX_TEMPLATE_SID "
                  "/ TWILIO_CUSTOM_CONTENT_SID to send outside the session window.")
        raise

    print(f"✅ WhatsApp message accepted by Twilio. SID: {message.sid} · status: {message.status}")

    # The create() call only confirms Twilio *accepted* the message, not that it
    # was delivered. Poll once, briefly, for a fast-fail signal so that shows up
    # in the Action logs instead of looking like a silent success.
    time.sleep(3)
    refreshed = client.messages(message.sid).fetch()
    print(f"📬 Delivery status after 3s: {refreshed.status}"
          + (f" (error {refreshed.error_code}: {refreshed.error_message})" if refreshed.error_code else ""))
    if refreshed.status in ("failed", "undelivered"):
        if refreshed.error_code == 63015:
            print("⚠️  Sandbox opt-in has likely expired — re-join via WhatsApp.")
        elif refreshed.error_code == 63016:
            print("⚠️  Outside the 24h session window and no template was used this "
                  "run — either re-join now, or set a template SID env var.")
        else:
            print("⚠️  Message was not delivered — see error code above.")

if __name__ == "__main__":
    dispatch_whatsapp_alerts()
