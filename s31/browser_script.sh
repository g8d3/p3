#!/bin/bash

source .env

a() { agent-browser --cdp "$CDP_PORT" "$@"; }
a open "$TARGET_URL"
a wait --load networkidle
a find label "$DOC_FIELD" fill "$DOC_VALUE"
a screenshot result.png