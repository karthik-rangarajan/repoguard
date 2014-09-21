from server import app
from flask import redirect

@app.route("/")
def index_route():
    return redirect("/static/index.html")

app.run(debug=True)

