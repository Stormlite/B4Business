import sys
import os

# Force Python to recognize the root directory for module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from twilio.rest import Client
from models.predict import score_todays_fixtures

def dispatch_whatsapp_alerts():
    """Identifies high-value value match selections and dispatches a Twilio summary alert."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    target_num = os.getenv("TARGET_WHATSAPP_NUMBER")
    
    if not all([account_sid, auth_token, target_num]):
        print("⚠️ Twilio credentials missing from environment. Skipping notification step.")
        return

    print("📡 Running valuation scanner for high-probability targets...")
    df = score_todays_fixtures()
    
    if df.empty:
        print("ℹ️ Notification engine: No games scheduled to analyze today.")
        return

    # Filter for matches with high confidence (> 75%)
    high_value_games = df[df["over_2_5_probability"] >= 0.75]
    
    if high_value_games.empty:
        print("ℹ️ Notification engine: No matches crossed the 75% selection threshold today.")
        return

    # Build message content body strings dynamically
    msg_body = "⚽ *DAILY OVER 2.5 GOALS CONFIDENCE PICKS* ⚽\n\n"
    for _, row in high_value_games.iterrows():
        pct = row['over_2_5_probability'] * 100
        msg_body += f"🔥 *{row['home_team']} vs {row['away_team']}*\n"
        msg_body += f"📈 Probability: *{pct:.2f}%*\n\n"
        
    msg_body += "🤖 _Automated forecast compiled daily via serverless ML pipeline._"

    # Execute outbound Twilio REST request connection
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=msg_body,
        from_="whatsapp:+14155238886",  # Standard sandbox phone number signature
        to=f"whatsapp:{target_num}"
    )
    print(f"✅ Outbound WhatsApp alert dispatched successfully! Status SID: {message.sid}")

if __name__ == "__main__":
    dispatch_whatsapp_alerts()
