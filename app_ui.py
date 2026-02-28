from flask import Flask, render_template_string
import requests

app = Flask(__name__)

API_BASE = "http://localhost:8000/admin/v1"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Taxi Admin Panel</title>
</head>
<body>
    <h1>Мини-сайт Taxi</h1>

    <form action="/drivers">
        <button type="submit">🚖 Водители</button>
    </form>

    <form action="/cars">
        <button type="submit">🚗 Машины</button>
    </form>

    <form action="/distances">
        <button type="submit">📍 Дистанции</button>
    </form>

    <hr>

    <h2>{{ title }}</h2>
    {% if data %}
        <table border="1" cellpadding="5" cellspacing="0">
            <tr>
                {% for key in data[0].keys() %}
                    <th>{{ key }}</th>
                {% endfor %}
            </tr>
            {% for row in data %}
                <tr>
                    {% for value in row.values() %}
                        <td>{{ value }}</td>
                    {% endfor %}
                </tr>
            {% endfor %}
        </table>
    {% else %}
        <p>Список пуст</p>
    {% endif %}

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, title="", data=[])

@app.route("/drivers")
def drivers():
    response = requests.get(f"{API_BASE}/drivers")
    data = response.json().get("drivers", [])
    return render_template_string(HTML_TEMPLATE, title="Список водителей", data=data)

@app.route("/cars")
def cars():
    response = requests.get(f"{API_BASE}/cars")
    data = response.json().get("cars", [])
    return render_template_string(HTML_TEMPLATE, title="Список машин", data=data)

@app.route("/distances")
def distances():
    response = requests.get(f"{API_BASE}/distances")
    data = response.json()  # Это уже список словарей
    return render_template_string(HTML_TEMPLATE, title="Список дистанций", data=data)

if __name__ == "__main__":
    app.run(debug=True)
