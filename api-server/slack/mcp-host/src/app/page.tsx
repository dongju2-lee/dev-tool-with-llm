import { HomeTemplate } from "@/components/templates/home";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "MCP Host",
};

export default function Home() {
  return (
    <div className="text-[#333] bg-gray-50">
      <HomeTemplate/>
    </div>
  );
}
