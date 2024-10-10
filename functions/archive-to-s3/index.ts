import { Handler, SQSEvent, SQSBatchResponse } from "aws-lambda";

export const handler: Handler<SQSEvent> = async (
  event,
  context
): Promise<SQSBatchResponse> => {
  const batchItemFailures = [];
  console.log(JSON.stringify(event));
  console.log(JSON.stringify(context));
  return { batchItemFailures };
};
