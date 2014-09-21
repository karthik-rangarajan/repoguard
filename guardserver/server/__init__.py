from flask import Flask, redirect
app = Flask(__name__, static_folder="../static")
app.config.from_object('config')

from issues import get_all_issues
