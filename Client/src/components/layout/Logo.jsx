// The logo in the current theme: navy lines on light backgrounds, light lines on dark ones.

export default function Logo({ className = "h-16 w-16" }) {
  return (
    <>
      <img src="/logo.svg" alt="" className={`${className} dark:hidden`} />
      <img src="/logo-dark.svg" alt="" className={`${className} hidden dark:block`} />
    </>
  );
}
