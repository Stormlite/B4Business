"""scripts/notify.py — WhatsApp alerts for high-confidence daily picks via Twilio"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.predict import score_todays_fixtures

def dispatch_whatsapp_alerts():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    target_num  = os.getenv("TARGET_WHATSAPP_NUMBER")
    content_sid = os.getenv("TWILIO_CONTENT_SID")  # see setup note below

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

    # WhatsApp only allows free-form (Body-only) business-initiated messages
    # within a 24-hour session window that opens when the recipient last
    # messaged the Twilio number. A fully automated daily push notification
    # will essentially always run outside that window — confirmed in
    # production by Twilio error 63016 ("outside the allowed messaging
    # window"). This applies to sandbox AND paid production numbers alike;
    # it's a WhatsApp platform rule, not a sandbox limitation.
    #
    # The only real fix is a pre-approved WhatsApp Message Template sent via
    # ContentSid + ContentVariables instead of a raw Body string. One-time
    # setup:
    #   1. Twilio Console → Messaging → Content Template Builder → create a
    #      WhatsApp template with ONE body variable, e.g.:
    #        "{{1}}"
    #      (a single variable holding the whole picks digest keeps this
    #      working without needing template re-approval every time the
    #      digest's content/structure changes)
    #   2. Submit for WhatsApp approval (usually fast, sometimes same-day)
    #   3. Once approved, set TWILIO_CONTENT_SID (repo secret) to that
    #      template's SID (starts with "HX...")
    # Until TWILIO_CONTENT_SID is set, this falls back to a free-form send,
    # which will reliably fail with 63016 outside a live session — useful
    # only for manual testing right after texting the bot yourself.
    try:
        if content_sid:
            message = client.messages.create(
                content_sid=content_sid,
                content_variables=json.dumps({"1": msg_body}),
                from_="whatsapp:+14155238886",
                to=f"whatsapp:{target_num}",
            )
        else:
            print("⚠️  TWILIO_CONTENT_SID not set — sending free-form, which will "
                  "fail with error 63016 unless you've messaged the bot in the "
                  "last 24 hours. See setup note in this file for the permanent fix.")
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
            print("   → Outside the 24h session window and no approved template was "
                  "used. Set TWILIO_CONTENT_SID — see setup note above this line.")
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
            print("⚠️  Outside the 24h session window. Set TWILIO_CONTENT_SID to send "
                  "via an approved template instead — see setup note above.")
        else:
            print("⚠️  Message was not delivered — see error code above.")

if __name__ == "__main__":
    dispatch_whatsapp_alerts()
