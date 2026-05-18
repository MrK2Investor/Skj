import argparse
import asyncio
import httpx

async def main():
    parser = argparse.ArgumentParser(description="Run Haystack volume compaction")
    parser.add_argument("volume_id", type=int)
    parser.add_argument("--haystack", default="http://localhost:8003")
    parser.add_argument("--admin-token", default="secret-admin-token")
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{args.haystack}/admin/compact/{args.volume_id}", headers={"x-admin-token": args.admin_token})
        resp.raise_for_status()
        print(resp.json())

if __name__ == "__main__":
    asyncio.run(main())
