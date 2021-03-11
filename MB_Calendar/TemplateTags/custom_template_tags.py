from django import template
register = template.Library()

# function to set python variables inside a template 
@register.simple_tag
def setvar(val=None):
  return val
