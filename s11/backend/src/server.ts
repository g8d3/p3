import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import dataRoutes from './routes/data';
import auditRoutes from './routes/audit';
import protectionRoutes from './routes/protection';

dotenv.config();

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

app.use('/api/data', dataRoutes);
app.use('/api/audit', auditRoutes);
app.use('/api/protection', protectionRoutes);

app.get('/', (req, res) => {
  res.send('Smart Contract Security API');
 });

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});