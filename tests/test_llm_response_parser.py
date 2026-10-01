"""Offline response-shape regressions; no provider, CMS, or publish requests."""
import json
import unittest
from unittest import mock

from src.llm_response import chat_text_from_response, json_from_chat_response, json_from_text


class FakeResponse:
    def __init__(self, body, payload=None):
        self.text = body
        self.payload = payload
        self.status_code = 200

    def json(self):
        if self.payload is None:
            return json.loads(self.text)
        return self.payload


PACKAGE = {"hero_title": "Fixture", "article_html": "<p>fixture</p>",
           "first_comment": "Read more", "caption": "Fixture caption", "hashtags": ["#fixture"]}


class ResponseParserTests(unittest.TestCase):
    def test_reasoning_prelude_and_fenced_package(self):
        text = '<think>example {not JSON}</think>\nHere is the package:\n```json\n' + json.dumps(PACKAGE) + '\n```'
        self.assertEqual(json_from_chat_response(FakeResponse(json.dumps({"choices": [{"message": {"content": text}}]}))), PACKAGE)

    def test_prose_multiple_braces_and_trailing_text(self):
        self.assertEqual(json_from_text('Note {unrelated}\n' + json.dumps(PACKAGE) + '\nDone {later}'), PACKAGE)

    def test_sse_delta_chunks_and_done(self):
        content = '<think>draft</think>\n```json\n' + json.dumps(PACKAGE) + '\n```'
        chunks = [content[:19], content[19:51], content[51:]]
        stream = '\n'.join('data: ' + json.dumps({"choices": [{"delta": {"content": part}}]}) for part in chunks)
        stream += '\ndata: [DONE]\n'
        self.assertEqual(json_from_chat_response(FakeResponse(stream)), PACKAGE)

    def test_sse_malformed_event_does_not_pollute_content(self):
        stream = 'data: invalid\ndata: ' + json.dumps({"choices": [{"delta": {"content": json.dumps(PACKAGE)}}]})
        self.assertEqual(chat_text_from_response(FakeResponse(stream)), json.dumps(PACKAGE))

    def test_plain_body_and_wrapped_envelope(self):
        self.assertEqual(json_from_chat_response(FakeResponse('```json\n' + json.dumps(PACKAGE) + '\n```')), PACKAGE)
        self.assertEqual(json_from_chat_response(FakeResponse('', {"response": {"choices": [{"message": {"content": json.dumps(PACKAGE)}}]}})), PACKAGE)
        self.assertEqual(json_from_chat_response(FakeResponse('', {"choices": [{"message": {"content": PACKAGE}}]})), PACKAGE)
        self.assertEqual(json_from_chat_response(FakeResponse('', {"output": [{"content": [{"type": "output_text", "text": json.dumps(PACKAGE)}]}]})), PACKAGE)

    def test_bounded_and_invalid_payloads(self):
        for text in ('', 'No valid JSON {broken}', 'x' * 1_000_001):
            with self.subTest(text_length=len(text)), self.assertRaisesRegex(ValueError, 'JSON hợp lệ'):
                json_from_text(text)

    def test_content_package_auto_fallback_and_explicit_llm_error(self):
        from src import content_packages as cp
        cfg = {"configured_base": "http://example.test/v1", "api_key": "fixture-private", "model": "fixture"}
        with mock.patch('src.content_builder.get_llm_candidates', return_value=cfg), mock.patch(
            'src.content_builder._get_task_model', return_value='fixture'
        ), mock.patch.object(cp, 'circuit_status', return_value={"open": False}), mock.patch.object(
            cp.requests, 'post', return_value=FakeResponse('invalid {broken}')
        ):
            result = cp.generate_package('Fixture', mode='auto')
            self.assertEqual(result['source'], 'no_llm_error_fallback')
            self.assertEqual(result['fallback_reason'], 'LLM response không chứa JSON hợp lệ')
            with self.assertRaisesRegex(RuntimeError, 'JSON hợp lệ'):
                cp.generate_package('Fixture', mode='llm')


if __name__ == '__main__':
    unittest.main()
