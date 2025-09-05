import os

import mysql.connector
import pandas as pd
import pdfkit
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key_here"


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


data = pd.read_csv('911.csv')
data['reason'] = data['title'].apply(lambda x: x.split(':')[0])
data['timeStamp'] = pd.to_datetime(data['timeStamp'], errors='coerce')  # Ensure datetime format


path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    total_calls = len(data)
    common_twp = data['twp'].value_counts().idxmax()
    return render_template('index.html', total_calls=total_calls, common_twp=common_twp)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('search', '').strip()
        selected_reason = request.form.get('reason', '')
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
    else:
        query = request.args.get('query', '').strip()
        selected_reason = request.args.get('reason', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

    filtered_data = data.copy()

    if query:
        filtered_data = filtered_data[filtered_data['twp'].str.contains(query, case=False, na=False)]

    if selected_reason:
        filtered_data = filtered_data[filtered_data['reason'] == selected_reason]

    if start_date:
        try:
            start_dt = pd.to_datetime(start_date)
            filtered_data = filtered_data[filtered_data['timeStamp'] >= start_dt]
        except Exception:
            pass

    if end_date:
        try:
            end_dt = pd.to_datetime(end_date)
            filtered_data = filtered_data[filtered_data['timeStamp'] <= end_dt]
        except Exception:
            pass

    total_calls = len(filtered_data)
    common_reason = filtered_data['reason'].value_counts().idxmax() if total_calls > 0 else "N/A"

    reasons_list = sorted(data['reason'].dropna().unique().tolist())

    return render_template(
        'search.html',
        query=query,
        results=filtered_data.to_dict(orient='records'),
        total_calls=total_calls,
        common_reason=common_reason,
        reasons=reasons_list,
        selected_reason=selected_reason,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/autocomplete')
def autocomplete():
    townships = sorted(data['twp'].dropna().unique().tolist())
    return jsonify(townships)

@app.route('/chart-data')
def chart_data():
    call_counts = data['reason'].value_counts()
    return jsonify({
        'labels': call_counts.index.tolist(),
        'values': call_counts.values.tolist()
    })

@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        password = request.form.get('password')
        if password != "Iam.2025":
            flash("Invalid admin password.", "danger")
            return redirect(url_for('upload_file'))

        file = request.files.get('file')
        if not file or file.filename == '':
            flash("No file selected.", "danger")
            return redirect(url_for('upload_file'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            global data
            data = pd.read_csv(filepath)
            data['reason'] = data['title'].apply(lambda x: x.split(':')[0])
            data['timeStamp'] = pd.to_datetime(data['timeStamp'], errors='coerce')

            flash("CSV uploaded and data updated successfully!", "success")
            return redirect(url_for('upload_file'))
        else:
            flash("Invalid file type. Please upload a CSV.", "danger")
            return redirect(url_for('upload_file'))

    return render_template('upload.html')

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    query = request.form.get('query', '').strip()
    selected_reason = request.form.get('reason', '')
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')

    filtered_data = data.copy()

    if query:
        filtered_data = filtered_data[filtered_data['twp'].str.contains(query, case=False, na=False)]

    if selected_reason:
        filtered_data = filtered_data[filtered_data['reason'] == selected_reason]

    if start_date:
        try:
            start_dt = pd.to_datetime(start_date)
            filtered_data = filtered_data[filtered_data['timeStamp'] >= start_dt]
        except Exception:
            pass

    if end_date:
        try:
            end_dt = pd.to_datetime(end_date)
            filtered_data = filtered_data[filtered_data['timeStamp'] <= end_dt]
        except Exception:
            pass

    total_calls = len(filtered_data)
    common_reason = filtered_data['reason'].value_counts().idxmax() if total_calls > 0 else "N/A"

    rendered = render_template(
        'search_pdf.html',
        query=query,
        results=filtered_data.to_dict(orient='records'),
        total_calls=total_calls,
        common_reason=common_reason
    )

    pdf = pdfkit.from_string(rendered, False, configuration=config)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=search_results_{query}.pdf'
    return response

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="root",           # change if needed
                password="",           # your MySQL root password if set
                database="emergency_portal"
            )
            cursor = conn.cursor()
            sql = "INSERT INTO feedback (name, email, message) VALUES (%s, %s, %s)"
            cursor.execute(sql, (name, email, message))
            conn.commit()
            cursor.close()
            conn.close()

            flash("Thank you for your feedback!", "success")
        except Exception as e:
            flash(f"An error occurred while saving feedback: {str(e)}", "danger")

        return redirect(url_for('feedback'))

    return render_template('feedback.html')

if __name__ == '__main__':
    app.run(debug=True)
