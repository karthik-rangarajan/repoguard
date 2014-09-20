# Application Config
DEBUG = True
SECRET_KEY = "secretkeybro"

LDAP_USERNAME = ""
LDAP_PASSWORD = ""

# LDAP Configuration
LDAP_DN = "cn=%s,ou=people,dc=example,dc=com"
LDAP_SERVER = ""

# Elastic Search Configuration
ELASTIC_HOST = "localhost"
ELASTIC_PORT = "9200"
INDEX = "repoguard"
DOC_TYPE = "repoguard"