curl --request POST \
  --url https://api.z.ai/api/coding/paas/v4/chat/completions \
  --header 'Accept-Language: en-US,en' \
  --header "Authorization: Bearer ${ZAI_API_KEY}" \
  --header 'Content-Type: application/json' \
  --data '
{
  "model": "glm-4.7-flashx",
  "messages": [
    {
      "role": "user",
      "content": "Write a poem about spring."
    }
  ],
  "stream": true,
  "temperature": 1
}
'
