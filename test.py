import asyncio

async def failed(*args, **kwargs):
    raise Exception(f"failed raised this: {str(args)}:{str(kwargs)}")

async def successful(*args, **kwargs):
    return f"sucessful with: {str(args)}:{str(kwargs)}"

async def main():
    ok, err = [], []
    for t in asyncio.as_completed([failed("1", 1), successful("2", 2), failed("3", 3), successful("4", 4)]):
        try:
            ok.append(await t)
        except Exception as error:
            err.append(f"failed with error: {error}")
    print(f"Successesful: {ok}, failed: {err}")

asyncio.run(main())