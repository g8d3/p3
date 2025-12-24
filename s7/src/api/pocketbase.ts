
import PocketBase from 'pocketbase';

const pb = new PocketBase('http://127.0.0.1:8090', {
  // Don't auto-load auth store to avoid blocking
});

export default pb;
