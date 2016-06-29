# -*- coding: utf-8 -*-

import datetime

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    db = DAL(settings.database_uri,fake_migrate_all=False)
    session.connect(request, response, masterapp='runestone', db=db)

else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db = db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'

#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Crud, Service, PluginManager, prettydate
from plugin_social_auth.utils import SocialAuth
auth = SocialAuth(db)
crud, service, plugins = Crud(db), Service(), PluginManager()

if settings.enable_captchas:
    ## Enable captcha's :-(
    from gluon.tools import Recaptcha
    auth.settings.captcha = Recaptcha(request,
        '6Lfb_t4SAAAAAB9pG_o1CwrMB40YPsdBsD8GsvlD',
        '6Lfb_t4SAAAAAGvAHwmkahQ6s44478AL5Cf-fI-x',
        options="theme:'blackglass'")

auth.settings.login_captcha = False
auth.settings.retrieve_password_captcha	= False
#auth.settings.retrieve_username_captcha	= False

plugins.social_auth.SOCIAL_AUTH_TWITTER_KEY = "foo"
plugins.social_auth.SOCIAL_AUTH_TWITTER_SECRET = "foo"
plugins.social_auth.SOCIAL_AUTH_FACEBOOK_KEY = "foo"
plugins.social_auth.SOCIAL_AUTH_FACEBOOK_SECRET = "foo"

# Configure PSA with all required backends
# Replace this by the backends that you want to use and have API keys for
plugins.social_auth.SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
    # You need this one to enable manual input for openid.
    # It must _not_ be configured in SOCIAL_AUTH_PROVIDERS (below)
    'social.backends.open_id.OpenIdAuth',

    'social.backends.live.LiveOAuth2',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.facebook.FacebookOAuth2')

# Configure the providers that you want to show in the login form.
# <backend name> : <display name>
# (You can find the backend name in the backend files as configured above.)
# Replace this by the backends you want to enable
plugins.social_auth.SOCIAL_AUTH_PROVIDERS = {
    'live': 'Live',
    'twitter': 'Twitter',
    'facebook': 'Facebook'}


plugins.social_auth.SOCIAL_AUTH_APP_INDEX_URL = URL('init', 'default', 'index')


## create all tables needed by auth if not custom tables
db.define_table('courses',
  Field('course_id','string'),
  Field('course_name', 'string', unique=True),
  Field('term_start_date', 'date'),
  Field('institution', 'string'),
  Field('base_course', 'string'),
  migrate='runestone_courses.table'
)
if db(db.courses.id > 0).isempty():
    db.courses.insert(course_name='boguscourse', term_start_date=datetime.date(2000, 1, 1)) # should be id 1
    db.courses.insert(course_name='thinkcspy', term_start_date=datetime.date(2000, 1, 1))
    db.courses.insert(course_name='pythonds', term_start_date=datetime.date(2000, 1, 1))
    db.courses.insert(course_name='overview', term_start_date=datetime.date(2000, 1, 1))

## create cohort_master table
db.define_table('cohort_master',
  Field('cohort_name','string',
  writable=False,readable=False),
  Field('created_on','datetime',default=request.now,
  writable=False,readable=False),
  Field('invitation_id','string',
  writable=False,readable=False),
  Field('average_time','integer', #Average Time it takes people to complete a unit chapter, calculated based on previous chapters
  writable=False,readable=False),
  Field('is_active','integer', #0 - deleted / inactive. 1 - active
  writable=False,readable=False),
  Field('course_name', 'string'),
  migrate='runestone_cohort_master.table'
  )
if db(db.cohort_master.id > 0).isempty():
    db.cohort_master.insert(cohort_name='Default Group', is_active = 1)

########################################

def getCourseNameFromId(courseid):
    ''' used to compute auth.user.course_name field '''
    if courseid == 1: # boguscourse
        return ''
    else:
        q = db.courses.id == courseid
        course_name = db(q).select()[0].course_name
        return course_name


def verifyInstructorStatus(course, instructor):
    """
    Make sure that the instructor specified is actually an instructor for the
    given course.
    """
    if type(course) == str:
        course = db(db.courses.course_name == course).select(db.courses.id).first()

    return db((db.course_instructor.course == course) &
             (db.course_instructor.instructor == instructor)
            ).count() > 0

class IS_COURSE_ID:
    ''' used to validate that a course name entered (e.g. devcourse) corresponds to a
        valid course ID (i.e. db.courses.id) '''
    def __init__(self, error_message='Unknown course name. Please see your instructor.'):
        self.e = error_message

    def __call__(self, value):
        if db(db.courses.course_name == value).select():
            return (db(db.courses.course_name == value).select()[0].id, None)
        return (value, self.e)

class HAS_NO_DOTS:
    def __init__(self, error_message='Your username may not contain a . or \' or space or any other special characters just letters and numbers'):
        self.e = error_message
    def __call__(self, value):
        if "." not in value and "'" not in value and " " not in value:
            return (value, None)
        return (value, self.e)
    def formatter(self, value):
        return value

db.define_table('auth_user',
    Field('username', type='string',
          label=T('Username')),
    Field('first_name', type='string',
          label=T('First Name')),
    Field('last_name', type='string',
          label=T('Last Name')),
    Field('email', type='string',
          requires=IS_EMAIL(banned='^.*shoeonlineblog\.com$'),
          label=T('Email')),
    Field('password', type='password',
          readable=False,
          label=T('Password')),
    Field('created_on','datetime',default=request.now,
          label=T('Created On'),writable=False,readable=False),
    Field('modified_on','datetime',default=request.now,
          label=T('Modified On'),writable=False,readable=False,
          update=request.now),
    Field('registration_key',default='',
          writable=False,readable=False),
    Field('reset_password_key',default='',
          writable=False,readable=False),
    Field('registration_id',default='',
          writable=False,readable=False),
    Field('cohort_id','reference cohort_master', requires=IS_IN_DB(db, 'cohort_master.id', 'id'),
          writable=False,readable=False),
    Field('course_id',db.courses,label=T('Course Name'),
          required=True,
          default=1),
    Field('course_name',compute=lambda row: getCourseNameFromId(row.course_id)),
    Field('active',type='boolean',writable=False,readable=False,default=True),
#    format='%(username)s',
    format=lambda u: u.first_name + " " + u.last_name,
    migrate='runestone_auth_user.table')


db.auth_user.first_name.requires = IS_NOT_EMPTY(error_message=auth.messages.is_empty)
db.auth_user.last_name.requires = IS_NOT_EMPTY(error_message=auth.messages.is_empty)
db.auth_user.password.requires = CRYPT(key=auth.settings.hmac_key)
db.auth_user.username.requires = (HAS_NO_DOTS(), IS_NOT_IN_DB(db, db.auth_user.username))
db.auth_user.registration_id.requires = IS_NOT_IN_DB(db, db.auth_user.registration_id)
db.auth_user.email.requires = (IS_EMAIL(error_message=auth.messages.invalid_email),
                               IS_NOT_IN_DB(db, db.auth_user.email))
db.auth_user.course_id.requires = IS_COURSE_ID()

auth.define_tables(username=True, signature=False, migrate='runestone_')

# create the instructor group if it doesn't already exist
if not db(db.auth_group.role == 'instructor').select().first():
    db.auth_group.insert(role='instructor')

## configure email
mail=auth.settings.mailer
mail.settings.server = 'logging' or 'smtp.gmail.com:587'
mail.settings.sender = 'you@gmail.com'
mail.settings.login = 'username:password'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

auth.settings.register_next = URL('default', 'index')

# change default session login time from 1 hour to 24 hours
auth.settings.expiration = 3600*24


db.define_table('user_courses',
                Field('user_id', 'string'),
                Field('course_id', 'string'),
                migrate='runestone_user_courses.table')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################


mail.settings.server = settings.email_server
mail.settings.sender = settings.email_sender
mail.settings.login = settings.email_login
