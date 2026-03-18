#!/bin/bash

# Define the core function
a() { 
    agent-browser --cdp 9222 "$@" 
}

echo "--- Browser Agent REPL ---"
echo "Type your commands (e.g., open \"google.com\"). Type 'exit' to quit."

while true; do
    # -e allows line editing (backspace, etc.)
    # -p sets the prompt string
    read -ep "browser> " input

    # Handle exit conditions
    [[ "$input" == "exit" || "$input" == "quit" ]] && break
    
    # Skip empty input
    [[ -z "$input" ]] && continue

    # Execute the input as arguments to function 'a'
    # eval allows the shell to respect quotes typed by the user
    eval "a $input"
done

echo "REPL closed."