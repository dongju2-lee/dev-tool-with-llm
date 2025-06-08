/* eslint-disable @typescript-eslint/no-explicit-any */
export enum EMcpServerType {
  LOCAL = "local",
  REMOTE = "remote",
}

export enum EMcpServerStatus {
  RUNNING = "running",
  PENDING = "pending",
  STOPPED = "stopped",
  ERROR = "error",
}

export type TToolProperty = {
  argName: string;
  type: string;
};

export type TTool = {
  name: string;
  properties: TToolProperty[];
};

export type TCallData = { [key: string]: string | number };

export type TToolHistory = {
  toolName?: string;
  toolArguments?: TCallData;
  message: string;
};

export type TMcpServer = {
  id: string; // UUID
  name: string; // 서버 이름
  desc: string; // 설명
  status: EMcpServerStatus; // 상태
  type: EMcpServerType; // 로컬 또는 원격
  url?: string; // 원격 서버인 경우 URL
  command?: string; // 로컬 서버인 경우 실행 명령어
  args: string[]; // 명령어 인자
  tools: any[]; // 서버가 제공하는 도구들
  histories: TToolHistory[]; // 도구 사용 기록
};
