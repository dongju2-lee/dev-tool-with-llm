/* eslint-disable @typescript-eslint/no-explicit-any */
import { ChatOpenAI } from "@langchain/openai";

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const LLM_MODEL = process.env.LLM_MODEL;
const OPENAI_URL = process.env.OPENAI_URL;

let config: any = {
  apiKey: OPENAI_API_KEY,
  model: LLM_MODEL,
};

if (OPENAI_URL) {
  config = {
    ...config,
    configuration: {
      baseURL: OPENAI_URL,
    },
  };
}

export const model = new ChatOpenAI(config);
export const model2 = new ChatOpenAI({
  model: "gpt-3.5-turbo",
  temperature: 0,
});
