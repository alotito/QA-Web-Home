import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser
from config_manager import get_config # Import the new function

def send_review_email(to_address, cc_addresses, subject, html_body):
    """
    Connects to the SMTP server and sends the review email.
    """
    smtp_server = get_config('Email', 'SMTPServer')
    smtp_port = int(get_config('Email', 'SMTPPort')) # config.getint is gone, so we cast to int
    from_address = get_config('Email', 'FromAddress')
    smtp_user = get_config('Email', 'User')
    smtp_password = get_config('Email', 'Password') 

    try:
        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = from_address
        msg['To'] = to_address
        msg['Cc'] = ", ".join(cc_addresses)
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        # Connect to the server and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_password) 

            recipients = [to_address] + cc_addresses
            server.sendmail(from_address, recipients, msg.as_string())

        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)
        
def generate_html_report(review_data):
    """
    Generates an HTML string for the email body based on the review data.
    """
    tech_name = review_data['technician_name']
    ticket_number = review_data['ticket_number']
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; color: #333; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 800px; margin-top: 20px; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            .fail {{ background-color: #ffdddd; }}
            h2, h3 {{ color: #0056b3; }}
            hr {{ border: 0; height: 1px; background: #ddd; }}
        </style>
    </head>
    <body>
        <h2>Quality Review for {tech_name} - Ticket #{ticket_number}</h2>
        <p><strong>Overall Comment:</strong> {review_data['overall_comment']}</p>
        <hr>
        <h3>Details:</h3>
        <table>
            <tr>
                <th>Question</th>
                <th>Observation</th>
                <th>Score</th>
            </tr>
    """

    total_score = 0
    max_score = 0

    for answer in review_data['answers']:
        score = float(answer['score'])
        max_points = float(answer['max_points'])
        total_score += score
        max_score += max_points
        
        row_class = ' class="fail"' if score < max_points else ''
        html += f"""
            <tr{row_class}>
                <td>{answer['question_text']}</td>
                <td>{answer['observation']}</td>
                <td>{score} / {max_points}</td>
            </tr>
        """

    final_percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    html += f"""
        </table>
        <h3 style="margin-top: 20px;">Final Score: {total_score} / {max_score} ({final_percentage:.2f}%)</h3>
    </body>
    </html>
    """
    return html
