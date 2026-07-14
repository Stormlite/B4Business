"""scripts/notify.py — WhatsApp alerts for high-confidence daily picks via Twilio"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predict import score_todays_fixtures

def dispatch_whatsapp_alerts():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    target_num  = os.getenv("TARGET_WHATSAPP_NUMBER")

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

    # NOTE: from_ number below (+14155238886) is Twilio's shared WhatsApp *Sandbox*
    # number, not a production sender. The sandbox requires the recipient to text
    # "join <sandbox-code>" to that number, and that opt-in EXPIRES 3 DAYS after
    # joining — after which sends silently fail to reach the phone even though the
    # API call itself can still succeed. If alerts have stopped arriving, first
    # check WhatsApp for a "sandbox session expired" style message and re-join.
    # For a permanent fix, register a production WhatsApp sender in the Twilio
    # console so this stops depending on a 3-day opt-in window.
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException

    client = Client(account_sid, auth_token)
    try:
        message = client.messages.create(
            body=msg_body,
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{target_num}",
        )
    except TwilioRestException as e:
        # Previously an exception here would still be unhandled by the time it
        # reached this point, but there was no diagnostic context printed first —
        # now we surface the likely cause before failing the job.
        print(f"❌ Twilio failed to send the WhatsApp message. Error {e.code}: {e.msg}")
        if e.code == 63015:
            print("   → The target number has not joined (or has fallen out of) "
                  "the Twilio Sandbox. Re-send the 'join <code>' message on WhatsApp.")
        raise

    print(f"✅ WhatsApp message accepted by Twilio. SID: {message.sid} · status: {message.status}")

    # The create() call only confirms Twilio *accepted* the message, not that it
    # was delivered. Poll once, briefly, for a fast-fail signal (e.g. sandbox
    # opt-in expired) so that shows up in the Action logs instead of looking
    # like a silent success.
    import time
    time.sleep(3)
    refreshed = client.messages(message.sid).fetch()
    print(f"📬 Delivery status after 3s: {refreshed.status}"
          + (f" (error {refreshed.error_code}: {refreshed.error_message})" if refreshed.error_code else ""))
    if refreshed.status in ("failed", "undelivered"):
        print("⚠️  Message was not delivered. If error 63015, the sandbox opt-in "
              "has likely expired — re-join via WhatsApp.")

if __name__ == "__main__":
    dispatch_whatsapp_alerts()
