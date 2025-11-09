HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            width: 90%;
            margin: 20px auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .header {{
            background-color: #d90429;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .content {{
            padding: 30px;
        }}
        .content table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .content th, .content td {{
            padding: 12px;
            border: 1px solid #eee;
            text-align: left;
        }}
        .content th {{
            background-color: #f9f9f9;
            width: 30%;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
            color: #777;
            background-color: #f9f9f9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>URGENT: Counterfeit Drug Report</h2>
        </div>
        <div class="content">
            <p>To the NAFDAC Anti-Counterfeit Taskforce,</p>
            <p>This is an automated, high-confidence report of a suspected counterfeit drug, submitted by a user via the <strong>ChecMed</strong> mobile application. The user has consented to share this data.</p>
            <p>Images of the product (box and blister pack) are attached.</p>
            
            <h3>Report Details:</h3>
            <table>
                <tr>
                    <th>Drug Name</th>
                    <td>{drug_name}</td>
                </tr>
                <tr>
                    <th>NAFDAC Number (User Input)</th>
                    <td>{nafdac_number}</td>
                </tr>
                <tr>
                    <th>Reason Flagged</th>
                    <td>{reason}</td>
                </tr>
                <tr>
                    <th>Approximate Location (LGA/City)</th>
                    <td>{location}</td>
                </tr>
            </table>

            <p style="margin-top: 20px;">This data can be used to identify counterfeit hotspots. Please review the attached images for verification.</p>
            <p>Thank you,</p>
            <p><strong>The ChecMed Platform</strong></p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ChecMed. Helping to keep Nigeria safe.</p>
        </div>
    </div>
</body>
</html>
"""