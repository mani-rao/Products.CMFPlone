## Script (Python) "plone_log"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=summary='',text=''
##title=
##
from zLOG import LOG, INFO
LOG('Plone Debug', INFO, summary, text)
