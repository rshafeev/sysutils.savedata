import json
import re
import os
import os.path

# Regular expression for comments
comment_re = re.compile(
    '(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
    re.DOTALL | re.MULTILINE
)
def parseFileJSON(filename):
    if not os.path.isfile(filename):
        raise Exception(" File '%s' not found. Please, add configuration file and try again.\nFailed.\n" % filename)
    content = open(filename).read()
    json_data = clear_json(content)
    return json.loads(json_data)

def clear_json(content):
    ## Looking for comments
    match = comment_re.search(content)
    while match:
        # single line comment
        content = content[:match.start()] + content[match.end():]
        match = comment_re.search(content)
    return content
    