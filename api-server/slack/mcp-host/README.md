# MCP Host by 멍개

멍개가 만든 MCP Host

```bash
$ npm i
```

```bash
$ npm run dev
```

### Mcp Server

```ts
import { FastMCP } from "fastmcp";
import { z } from "zod"; 

const server = new FastMCP({
  name: "My Server",
  version: "1.0.0",
});

server.addTool({
  name: "add",
  description: "Add two numbers",
  parameters: z.object({
    a: z.number(),
    b: z.number(),
  }),
  execute: async (args) => {
    console.log("add");
    console.log(args);
    return String(args.a + args.b);
  },
});

server.addTool({
  name: "multifly",
  description: "Add two multifly",
  parameters: z.object({
    a: z.number(),
    b: z.number(),
  }),
  execute: async (args) => {
    console.log("multifly");
    console.log(args);
    return String(args.a * args.b);
  },
});

server.start({
  transportType: "sse",
  sse: {
    endpoint: "/sse",
    port: 8080,
  },
});

/*
server.start({
  transportType: "stdio",
});
*/
```