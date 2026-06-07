from crew.crew_runner import crew


def test_ord1005_investigation():
    result = crew.kickoff()

    result_text = str(result)

    assert "ORD1005" in result_text
    assert "Delayed" in result_text