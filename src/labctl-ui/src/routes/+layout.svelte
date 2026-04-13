<script lang="ts">
  import { onMount } from "svelte";

  import "../app.css";
  import favicon from "$lib/assets/favicon.svg";

  let { children } = $props();

  onMount(() => {
    // document.documentElement.classList.add('dark');
    document.body.classList.add("bg-background", "text-foreground");

    return () => {
      document.body.classList.remove("bg-background", "text-foreground");
    };
  });
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

{@render children()}
