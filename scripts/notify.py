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

    # Use the model's high_conf_pick flag (≥62% confidence) instead of a hard 75% cut
    if "high_conf_pick" in df.columns:
        picks = df[df["high_conf_pick"] == True]
    else:
        picks = df[df["over_2_5_probability"] >= 0.62]

    if picks.empty:
        print("ℹ️  No high-confidence picks today.")
        return

    msg_body = "⚽ *B4Business Daily Picks* ⚽\n\n"
    for _, row in picks.iterrows():
        o25  = row["over_2_5_probability"] * 100
        btts = row.get("btts_probability", 0) * 100
        time_= row.get("match_time", "")
        msg_body += f"🔥 *{row['home_team']} vs {row['away_team']}*"
        if time_: msg_body += f"  ⏰ {time_}"
        msg_body += f"\n   Over 2.5: *{o25:.1f}%*  ·  BTTS: *{btts:.1f}%*\n\n"

    msg_body += "_Automated forecast · B4Business ML pipeline_"

    from twilio.rest import Client
    client  = Client(account_sid, auth_token)
    message = client.messages.create(
        body=msg_body,
        from_="whatsapp:+14155238886",
        to=f"whatsapp:{target_num}",
    )
    print(f"✅ WhatsApp alert sent. SID: {message.sid}")

if __name__ == "__main__":
    dispatch_whatsapp_alerts()
