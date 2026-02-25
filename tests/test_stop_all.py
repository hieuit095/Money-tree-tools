from app import docker_manager


class _FakeContainer:
    def __init__(self, *, status: str, labels: dict[str, str]):
        self.status = status
        self.labels = labels
        self.stopped = False
        self.stop_args = None

    def stop(self, timeout: int = 0):
        self.stopped = True
        self.stop_args = {"timeout": timeout}


class _FakeDockerClient:
    def __init__(self, containers):
        self._containers = containers

    class containers:
        pass

    def containers_list(self, all: bool = False):
        return list(self._containers)


def test_stop_all_stops_only_managed_running(monkeypatch):
    c1 = _FakeContainer(status="running", labels={"project": "standard"})
    c2 = _FakeContainer(status="running", labels={"project": "proxy"})
    c3 = _FakeContainer(status="running", labels={"com.docker.compose.project": docker_manager.IGM_PROJECT_NAME})
    c4 = _FakeContainer(status="exited", labels={"project": "standard"})
    c5 = _FakeContainer(status="running", labels={})

    fake = _FakeDockerClient([c1, c2, c3, c4, c5])

    def get_client():
        class Obj:
            def __init__(self, containers):
                self._containers = containers

            class containers:
                pass

        obj = Obj(fake._containers)

        def _list(all: bool = False):
            return list(obj._containers)

        obj.containers.list = _list
        return obj

    monkeypatch.setattr(docker_manager, "get_client", get_client)

    ok, msg = docker_manager.stop_all()
    assert ok is True
    assert msg == "Success"
    assert c1.stopped is True
    assert c2.stopped is True
    assert c3.stopped is True
    assert c4.stopped is False
    assert c5.stopped is False

