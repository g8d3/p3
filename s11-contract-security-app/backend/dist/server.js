"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const dotenv_1 = __importDefault(require("dotenv"));
const data_1 = __importDefault(require("./routes/data"));
const audit_1 = __importDefault(require("./routes/audit"));
const protection_1 = __importDefault(require("./routes/protection"));
dotenv_1.default.config();
const app = (0, express_1.default)();
const port = process.env.PORT || 3001;
app.use((0, cors_1.default)());
app.use(express_1.default.json());
app.use('/api/data', data_1.default);
app.use('/api/audit', audit_1.default);
app.use('/api/protection', protection_1.default);
app.get('/', (req, res) => {
    res.send('Smart Contract Security API');
});
app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
