from django import template
register = template.Library()

@register.simple_tag
def setvar(val=None):
  return val

@register.simple_tag
def increment(num):
  return num+1
