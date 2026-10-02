"""Offline response-shape regressions; no provider, CMS, or publish requests."""
import json
import unittest
from unittest import mock

from src.llm_response import chat_model_unavailable, chat_stream_incomplete, chat_text_from_response, json_from_chat_response, json_from_text


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

    def test_incomplete_stream_is_not_retried_or_counted_as_llm(self):
        from src import content_packages as cp
        stream = 'data: ' + json.dumps({'choices': [{'delta': {'content': 'partial answer'}}]})
        self.assertTrue(chat_stream_incomplete(FakeResponse(stream)))
        self.assertFalse(chat_stream_incomplete(FakeResponse(stream + '\ndata: [DONE]')))
        cfg = {"configured_base": "http://example.test/v1", "api_key": "fixture-private", "model": "fixture"}
        with mock.patch('src.content_builder.get_llm_candidates', return_value=cfg), mock.patch(
            'src.content_builder._get_task_model', return_value='fixture'
        ), mock.patch.object(cp, 'circuit_status', return_value={"open": False}), mock.patch.object(
            cp.requests, 'post', return_value=FakeResponse(stream)
        ) as post:
            with self.assertRaisesRegex(RuntimeError, 'stream ended without completion'):
                cp.generate_package('Fixture', mode='llm')
            self.assertEqual(post.call_count, 1)
            self.assertEqual(cp.generate_package('Fixture', mode='auto')['source'], 'no_llm_error_fallback')
            self.assertEqual(post.call_count, 2)

    def test_plain_body_and_wrapped_envelope(self):
        self.assertEqual(json_from_chat_response(FakeResponse('```json\n' + json.dumps(PACKAGE) + '\n```')), PACKAGE)
        self.assertEqual(json_from_chat_response(FakeResponse('', {"response": {"choices": [{"message": {"content": json.dumps(PACKAGE)}}]}})), PACKAGE)
        self.assertEqual(json_from_chat_response(FakeResponse('', {"choices": [{"message": {"content": PACKAGE}}]})), PACKAGE)
        self.assertEqual(json_from_chat_response(FakeResponse('', {"output": [{"content": [{"type": "output_text", "text": json.dumps(PACKAGE)}]}]})), PACKAGE)

    def test_bounded_and_invalid_payloads(self):
        for text in ('', 'No valid JSON {broken}', 'x' * 1_000_001):
            with self.subTest(text_length=len(text)), self.assertRaisesRegex(ValueError, 'JSON hợp lệ'):
                json_from_text(text)

    def test_retired_model_notice_is_not_a_json_failure_or_retried(self):
        from src import content_packages as cp
        notice = 'Gemini 3.1 is no longer available. Please switch to a supported model in the latest version.'
        response = FakeResponse(json.dumps({'choices': [{'message': {'content': notice}, 'finish_reason': 'stop'}]}))
        self.assertTrue(chat_model_unavailable(response))
        self.assertFalse(chat_model_unavailable(FakeResponse(json.dumps({'choices': [{'message': {'content': json.dumps(PACKAGE)}}]}))))
        cfg = {'configured_base': 'http://example.test/v1', 'api_key': 'fixture-private', 'model': 'fixture'}
        with mock.patch('src.content_builder.get_llm_candidates', return_value=cfg), mock.patch(
            'src.content_builder._get_task_model', return_value='fixture'
        ), mock.patch.object(cp, 'circuit_status', return_value={'open': False}), mock.patch.object(
            cp.requests, 'post', return_value=response
        ) as post:
            with self.assertRaisesRegex(RuntimeError, 'model is no longer available'):
                cp.generate_package('Fixture', mode='llm')
            self.assertEqual(post.call_count, 1)
            result = cp.generate_package('Fixture', mode='auto')
            self.assertEqual(result['source'], 'no_llm_error_fallback')
            self.assertIn('model is no longer available', result['fallback_reason'])
            self.assertEqual(post.call_count, 2)

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

    def test_content_package_one_adjusted_retry_then_llm_success(self):
        from src import content_packages as cp
        cfg = {"configured_base": "http://example.test/v1", "api_key": "fixture-private", "model": "fixture"}
        calls = []
        def post(url, **kwargs):
            calls.append(kwargs['json'])
            return FakeResponse('reasoning only') if len(calls) == 1 else FakeResponse(json.dumps({
                "choices": [{"message": {"content": json.dumps({**PACKAGE, "first_comment": ""})}}]
            }))
        with mock.patch('src.content_builder.get_llm_candidates', return_value=cfg), mock.patch(
            'src.content_builder._get_task_model', return_value='fixture'
        ), mock.patch.object(cp, 'circuit_status', return_value={"open": False}), mock.patch.object(
            cp.requests, 'post', side_effect=post
        ), mock.patch.object(cp, 'record_llm_success') as success:
            result = cp.generate_package('Fixture', mode='llm')
        self.assertEqual(result['source'], 'llm')
        self.assertEqual(result['first_comment'], '')
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(calls[1]['messages']), 2)
        success.assert_called_once()

    def test_content_package_comment_requires_exact_article_url(self):
        from src import content_packages as cp
        cfg = {"configured_base": "http://example.test/v1", "api_key": "fixture-private", "model": "fixture"}
        article_url = "https://example.test/article/one"
        calls = []
        def post(url, **kwargs):
            calls.append(kwargs["json"])
            comment = "Generic comment" if len(calls) == 1 else f"Specific video detail: {article_url}"
            return FakeResponse(json.dumps({"choices": [{"message": {"content": json.dumps({**PACKAGE, "first_comment": comment})}}]}))
        with mock.patch('src.content_builder.get_llm_candidates', return_value=cfg), mock.patch(
            'src.content_builder._get_task_model', return_value='fixture'
        ), mock.patch.object(cp, 'circuit_status', return_value={"open": False}), mock.patch.object(
            cp.requests, 'post', side_effect=post
        ), mock.patch.object(cp, 'record_llm_success'):
            result = cp.generate_package('Fixture', mode='llm', article_url=article_url)
        self.assertEqual(result['first_comment_source'], 'llm')
        self.assertIn(article_url, result['first_comment'])
        self.assertIn(article_url, calls[0]['messages'][0]['content'])
        self.assertEqual(len(calls), 2)

    def test_http_and_quota_are_not_retried_or_misreported_as_llm(self):
        from src import content_packages as cp
        cfg = {"configured_base": "http://example.test/v1", "api_key": "fixture-private", "model": "fixture"}
        with mock.patch('src.content_builder.get_llm_candidates', return_value=cfg), mock.patch(
            'src.content_builder._get_task_model', return_value='fixture'
        ), mock.patch.object(cp, 'circuit_status', return_value={"open": False}), mock.patch.object(
            cp, 'record_quota_failure', return_value={'open': True}
        ) as record, mock.patch.object(cp.requests, 'post') as post:
            post.return_value = FakeResponse('')
            post.return_value.status_code = 429
            with self.assertRaisesRegex(RuntimeError, 'quota HTTP 429'):
                cp.generate_package('Fixture', mode='llm')
            record.assert_not_called()
            self.assertEqual(post.call_count, 1)
            auto = cp.generate_package('Fixture', mode='auto')
            self.assertEqual(auto['source'], 'no_llm_quota_fallback')
            self.assertEqual(post.call_count, 2)

    def test_invalid_twice_auto_marks_fallback_and_explicit_llm_fails(self):
        from src import content_packages as cp
        cfg = {"configured_base": "http://example.test/v1", "api_key": "fixture-private", "model": "fixture"}
        with mock.patch('src.content_builder.get_llm_candidates', return_value=cfg), mock.patch(
            'src.content_builder._get_task_model', return_value='fixture'
        ), mock.patch.object(cp, 'circuit_status', return_value={"open": False}), mock.patch.object(
            cp.requests, 'post', return_value=FakeResponse('reasoning only')
        ) as post:
            result = cp.generate_package('Fixture', mode='auto')
            self.assertEqual(result['source'], 'no_llm_error_fallback')
            self.assertEqual(post.call_count, 2)
            with self.assertRaisesRegex(RuntimeError, 'JSON hợp lệ'):
                cp.generate_package('Fixture', mode='llm')
            self.assertEqual(post.call_count, 4)


if __name__ == '__main__':
    unittest.main()
