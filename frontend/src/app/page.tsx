import { ApiStatus } from "@/components/ApiStatus";

export default function Home() {
  return (
    <section aria-labelledby="home-title">
      <h1 id="home-title">EdgeLedger</h1>
      <p>Research workspace and tracker. Modules are under construction.</p>
      <ApiStatus />
    </section>
  );
}
