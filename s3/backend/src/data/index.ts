import ProjectDataSource from './ProjectDataSource'
import TableDataSource from './TableDataSource'
import WorkflowDataSource from './WorkflowDataSource'
import FieldDataSource from './FieldDataSource'

export default {
  project: new ProjectDataSource(),
  table: new TableDataSource(),
  workflow: new WorkflowDataSource(),
  field: new FieldDataSource(),
}
