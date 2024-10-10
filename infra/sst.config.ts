/// <reference path="./.sst/platform/config.d.ts" />
import { readFileSync } from "node:fs";
import * as toml from "toml";
import { load } from "ts-dotenv";

// SST will move the source files to `.sst/platform` directory
const PROJECT_ROOT = `${import.meta.dirname}/../../..`;

const PYPROJECT = toml.parse(
  readFileSync(`${PROJECT_ROOT}/api/pyproject.toml`, "utf-8")
);

const env = load({
  APP_ENV: String,
  APP_NAME: { default: PYPROJECT.project.name, type: String },
  APP_VERSION: { default: PYPROJECT.project.version, type: String },

  HOST: String,
  PORT: Number,

  LOG_LEVEL: String,

  SST_STAGE: String,
});

export default $config({
  app(input) {
    return {
      home: "aws",
      name: env.APP_NAME,
      removal: env.SST_STAGE === "prod" ? "retain" : "remove",
      // version: env.APP_VERSION // this is the "sst" version, not the app version
    };
  },
  async run() {
    if (["dev", "prod"].includes($app.stage) === false) {
      throw new Error(
        `invalid stage: must be "dev" or "prod", received: "${$app.stage}"`
      );
    }

    const SUFFIX = `${env.APP_NAME}-${$app.stage}`;

    const vpc = new sst.aws.Vpc(`vpc-${SUFFIX}`);

    const databasePostgres = new sst.aws.Postgres(`postgres-${SUFFIX}`, {
      vpc,
    });

    const bucketArchive = new sst.aws.Bucket(`bucket-archive-${SUFFIX}`);
    const queueArchive = new sst.aws.Queue(`sqs-archive-${SUFFIX}`);
    const functionArchive = new sst.aws.Function(`function-archive-${SUFFIX}`, {
      architecture: "arm64",
      handler: `${PROJECT_ROOT}/functions/archive-to-s3/index.handler`,
      runtime: "nodejs20.x",
      permissions: [
        {
          actions: [
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes",
            "sqs:ReceiveMessage",
          ],
          resources: [queueArchive.arn],
        },
        {
          actions: ["s3:PutObject"],
          resources: [bucketArchive.arn],
        },
      ],
      transform: {
        function: {
          tracingConfig: {
            mode: "Active",
          },
        },
        role: {
          managedPolicyArns: [
            "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
          ],
        },
      },
    });
    queueArchive.subscribe(functionArchive.arn, {
      batch: {
        partialResponses: true,
        window: "5 seconds",
      },
    });

    const cluster = new sst.aws.Cluster(`ecs-cluster-${SUFFIX}`, { vpc });
    cluster.addService(`ecs-service-${SUFFIX}`, {
      environment: {
        APP_ENV: env.APP_ENV,
        APP_NAME: env.APP_NAME,
        APP_VERSION: env.APP_VERSION,

        HOST: env.HOST,
        PORT: `${env.PORT}`,

        LOG_LEVEL: env.LOG_LEVEL,

        PSQL_DATABASE: $interpolate`${databasePostgres.database}`,
        PSQL_HOST: $interpolate`${databasePostgres.host}`,
        PSQL_PASSWORD: $interpolate`${databasePostgres.password}`,
        PSQL_PORT: $interpolate`${databasePostgres.port}`,
        PSQL_USER: $interpolate`${databasePostgres.username}`,

        QUEUE_ARCHIVE_URL: $interpolate`${queueArchive.url}`,

        // https://github.com/aws/amazon-ecs-agent/blob/master/README.md
        ECS_CONTAINER_STOP_TIMEOUT: "5s",
        ECS_IMAGE_PULL_BEHAVIOR: "once",
      },
      image: {
        context: "../api",
      },
      permissions: [
        {
          actions: ["sqs:SendMessage"],
          resources: [queueArchive.arn],
        },
      ],
      public: {
        ports: [{ listen: "80/http", forward: `${env.PORT}/http` }],
      },
      transform: {
        service: {
          // https://nathanpeck.com/speeding-up-amazon-ecs-container-deployments/
          deploymentMaximumPercent: 200,
          deploymentMinimumHealthyPercent: 50,
          desiredCount: 1,
          forceNewDeployment: true,
          waitForSteadyState: true,
        },
        target: {
          // https://nathanpeck.com/speeding-up-amazon-ecs-container-deployments/
          deregistrationDelay: 5,
          healthCheck: {
            healthyThreshold: 2,
            interval: 8,
            path: "/health",
            timeout: 5,
          },
        },
      },
    });
  },
});
