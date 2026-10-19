"""Raw SOAP call to worldserver (AC uses SOAP header auth, not xmlrpc)."""
import http.client
import sys

body = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
    'xmlns:ns1="urn:AC">'
    '<SOAP-ENV:Header><ns1:username>%s</ns1:username><ns1:password>%s</ns1:password></SOAP-ENV:Header>'
    '<SOAP-ENV:Body><ns1:executeCommand><command>%s</command></ns1:executeCommand></SOAP-ENV:Body>'
    "</SOAP-ENV:Envelope>"
) % (sys.argv[1], sys.argv[2], sys.argv[3])

conn = http.client.HTTPConnection("127.0.0.1", 7878, timeout=15)
conn.request(
    "POST",
    "/",
    body,
    {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '"urn:AC#executeCommand"'},
)
r = conn.getresponse()
print("HTTP", r.status)
print(r.read().decode(errors="replace"))
