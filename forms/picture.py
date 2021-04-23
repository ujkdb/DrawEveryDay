from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired


class UploadForm(FlaskForm):
    picture = FileField(validators=[FileRequired()])
