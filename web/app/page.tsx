import { Receipt } from "../components/Receipt";
import { sampleReceipt } from "../lib/fixture";

export default function Home() {
  return <Receipt payload={sampleReceipt} />;
}
