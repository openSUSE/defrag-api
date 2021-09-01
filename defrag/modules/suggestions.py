from datetime import datetime, timedelta
from pydantic.main import BaseModel
from defrag.modules.helpers.sync_utils import as_async
from typing import Any, Dict, List, Optional
from defrag.modules.db.redis import RedisPool
from defrag import app
from defrag.modules.helpers import QueryResponse, EitherErrorOrOk, Query
from math import sqrt
from pottery import RedisDict

__MODULE_NAME__ = "suggestions"


class Suggestions:

    class New(BaseModel):
        title: str
        description: str
        creator_id: str
        start_datetime: Optional[str] = None
        end_datetime: Optional[str] = None

    container = RedisDict(
        {}, redis=RedisPool().connection, key="suggestions")

    @classmethod
    async def add(cls, new_suggestion: New) -> EitherErrorOrOk:
        instance: Suggestions = cls(**new_suggestion.dict())
        if not instance.key in cls.container:
            await as_async(lambda: cls.container.__setitem__(instance.key, instance.dict()))()
            return EitherErrorOrOk(ok=instance.key, ok_msg="Thanks for voting!")
        return EitherErrorOrOk(error=f"Unable to add this key {instance.key}, as the same exists already.")

    @classmethod
    async def remove(cls, key: str) -> None:
        if not key in cls.container:
            return

        def removing(key: str) -> None:
            item = cls.container[key]
            if datetime.now() - datetime.fromtimestamp(item["created"]) < timedelta(days=1):
                cls.container.__delitem__(key)
        return await as_async(removing)(key)

    @classmethod
    async def cast_vote(cls, voter_id: str, key: str, vote: int) -> EitherErrorOrOk:
        def voting(key: str, voter_id: str, vote: int):
            item = cls.container[key]
            if voter_id in item["voters_ids"]:
                return
            if vote == 1:
                item["votesFor"] += 1
            else:
                item["votesAgainst"] += 1
            item["score"] = cls.make_score(
                _for=item["votesFor"], _against=item["votesAgainst"])
            item["voters_ids"].append(voter_id)
            cls.container[key] = item
        if key in cls.container:
            await as_async(voting)(key, voter_id, vote)
            return EitherErrorOrOk(ok=f"Thanks for voting for {key}")
        return EitherErrorOrOk(error=f"You tried to vote for {key}, which is not a valid key!")

    def __init__(
        self,
        title: str,
        description: str,
        creator_id: str,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None
    ) -> None:
        self.key = str(abs(hash(title)))
        self.title = title
        self.description = description
        self.creator_id = creator_id
        if end_datetime:
            self.end_datetime = end_datetime
        self.votesFor: int = 1
        self.votesAgainst: int = 0
        self.score: float = 0
        self.voters_ids: List[str] = [creator_id]
        self.created: float = datetime.now().timestamp()
        self.start_datetime: str = start_datetime or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def dict(self) -> Dict[str, Any]:
        return vars(self)

    @staticmethod
    def make_score(_for: int, _against: int) -> float:
        """ aka lower bound of Wilson score confidence interval for a Bernoulli parameter """
        left = (_for + 1.9208) / (_for + _against)
        right = 1.96 * sqrt((_for * _against) / (_for + _against) + 0.9604) / \
            (_for + _against) / (1 + 3.8416 / (_for + _against))
        return round(left - right, 3)

    @staticmethod
    async def view(key: Optional[str] = None) -> EitherErrorOrOk:
        if not key:
            return await as_async(lambda: sorted(Suggestions.container.values(), key=lambda i: i["score"], reverse=True))()
        if key and not key in Suggestions.container:
            return EitherErrorOrOk(error=f"You were looking for this key {key} but it could not be found!")
        return EitherErrorOrOk(ok=await as_async(lambda: Suggestions.container[key])())


@app.get(f"/{__MODULE_NAME__}/")
async def get_suggestions(key: Optional[str] = None) -> QueryResponse:
    query = Query(service=__MODULE_NAME__)
    results = await Suggestions.view(key)
    if ok := results.is_ok:
        return QueryResponse(query=query, results=ok, results_count=len(ok))
    return QueryResponse(query=query, error=results.error)


@app.post(f"/{__MODULE_NAME__}/create/")
async def create_suggestion(sugg: Suggestions.New) -> QueryResponse:
    query = Query(service=__MODULE_NAME__)
    result = await Suggestions.add(sugg)
    if result.is_ok:
        return QueryResponse(query=query, message="Thanks!")
    return QueryResponse(query=query, error="Didn't turn out the way we anticipated!")


@app.post(f"/{__MODULE_NAME__}/vote_for_suggestion/")
async def vote_for_suggestion(voter_id: str, sugg_id: str, vote: int) -> QueryResponse:
    query = Query(service=__MODULE_NAME__)
    result = await Suggestions.cast_vote(voter_id=voter_id, key=sugg_id, vote=vote)
    if result.is_ok:
        return QueryResponse(query=query, message="Thanks!")
    return QueryResponse(query=query, error=result.error)
