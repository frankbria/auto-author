/**
 * Loading Utilities
 *
 * Time estimation and progress tracking for async operations
 */

export {
  estimateOperationTime,
  formatTime,
  getProgressEstimate,
  createProgressTracker,
  OPERATION_TIME_BUDGETS,
} from './timeEstimator';

export type {
  TimeEstimate,
  OperationMetadata,
} from './timeEstimator';
