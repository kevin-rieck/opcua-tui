from opcua_tui import main as main_module


def test_main_calls_run(monkeypatch) -> None:
    called: list[bool] = []

    def fake_run() -> None:
        called.append(True)

    monkeypatch.setattr(main_module, "run", fake_run)

    main_module.main()

    assert called == [True]
