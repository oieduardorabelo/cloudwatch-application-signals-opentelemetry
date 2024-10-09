/// <reference path="./.sst/platform/config.d.ts" />
import { readFileSync } from "node:fs";
import * as toml from "toml";
import { load } from "ts-dotenv";

const PYPROJECT = toml.parse(
  readFileSync(`${import.meta.dirname}/../../../api/pyproject.toml`, "utf-8")
);

const env = load({
  APP_ENV: String,
  APP_NAME: { default: PYPROJECT.project.name, type: String },
  APP_VERSION: { default: PYPROJECT.project.version, type: String },

  HOST: String,
  PORT: Number,

  LOG_LEVEL: String,

  PSQL_DATABASE: String,
  PSQL_HOST: String,
  PSQL_PASSWORD: String,
  PSQL_USER: String,

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
    const cluster = new sst.aws.Cluster(`ecs-cluster-${SUFFIX}`, { vpc });
    cluster.addService(`ecs-service-${SUFFIX}`, {
      environment: {
        APP_ENV: env.APP_ENV,
        APP_NAME: env.APP_NAME,
        APP_VERSION: env.APP_VERSION,

        HOST: env.HOST,
        PORT: `${env.PORT}`,

        LOG_LEVEL: env.LOG_LEVEL,

        PSQL_DATABASE: env.PSQL_DATABASE,
        PSQL_HOST: env.PSQL_HOST,
        PSQL_PASSWORD: env.PSQL_PASSWORD,
        PSQL_USER: env.PSQL_USER,

        // https://github.com/aws/amazon-ecs-agent/blob/master/README.md
        ECS_CONTAINER_STOP_TIMEOUT: "5s",
        ECS_IMAGE_PULL_BEHAVIOR: "once",
      },
      image: {
        context: "../api",
      },
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
            interval: 5,
            path: "/health",
            timeout: 4,
          },
        },
      },
    });
  },
});
