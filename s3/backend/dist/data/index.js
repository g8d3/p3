"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const ProjectDataSource_1 = __importDefault(require("./ProjectDataSource"));
const TableDataSource_1 = __importDefault(require("./TableDataSource"));
const WorkflowDataSource_1 = __importDefault(require("./WorkflowDataSource"));
const FieldDataSource_1 = __importDefault(require("./FieldDataSource"));
exports.default = {
    project: new ProjectDataSource_1.default(),
    table: new TableDataSource_1.default(),
    workflow: new WorkflowDataSource_1.default(),
    field: new FieldDataSource_1.default(),
};
