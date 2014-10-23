from wtforms import Form, BooleanField, validators

class ConfirmForm(Form):
  confirm = BooleanField('Yes.', [validators.Required()])

