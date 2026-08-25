import os
import json
from typing import Dict, Any, Optional, Type, Union
import google.genai as genai
from google.genai import types
from pydantic import BaseModel

from backend.utils.logger import get_logger
from backend.core.config import settings
from backend.core import demo_config
from backend.utils.exceptions import LLMError, APIRequestError

logger = get_logger(__name__)

class GeminiClient:
    """Gemini Client using google-genai SDK"""

    def __init__(self):
        if demo_config.is_demo_mode():
            logger.warning(
                "GeminiClient constructed while demo mode is active for at least one "
                "stage; client will refuse real generation calls."
            )
        self.api_key = settings.google_api_key
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found in settings.")

        # Initialize the client
        # connection options can be added here if needed
        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini Client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self.client = None

    async def generate_content(self, model: str, prompt: str, config: Optional[types.GenerateContentConfig] = None) -> str:
        """
        Generate text content using Gemini.

        Args:
            model: Model name (e.g., 'gemini-3-pro-preview')
            prompt: User prompt
            config: Optional generation config

        Returns:
            Generated text
        """
        if demo_config.is_active_stage_demo_or_any():
            raise LLMError("Refusing real Gemini call: demo mode is active for this request stage")
        if not self.client:
            raise LLMError("Gemini Client not initialized")

        try:
            logger.info(f"Calling Gemini model: {model}")

            # Use async client
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )

            if response.text:
                return response.text
            return ""

        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise APIRequestError(f"Gemini API Error: {e}")

    async def generate_structured_content(
        self,
        model: str,
        prompt: str,
        response_schema: Union[Type[BaseModel], Dict[str, Any]],
        config: Optional[types.GenerateContentConfig] = None
    ) -> Dict[str, Any]:
        """
        Generate structured content (JSON) using Gemini.

        Args:
            model: Model name
            prompt: User prompt
            response_schema: Pydantic model or Dict schema
            config: Optional generation config

        Returns:
            Parsed JSON dict
        """
        if demo_config.is_active_stage_demo_or_any():
            raise LLMError("Refusing real Gemini call: demo mode is active for this request stage")
        if not self.client:
            raise LLMError("Gemini Client not initialized")

        try:
            logger.info(f"Calling Gemini structured model: {model}")

            if config is None:
                config = types.GenerateContentConfig()

            # Set response MIME type to JSON
            config.response_mime_type = "application/json"
            config.response_schema = self._sanitize_schema(response_schema)

            response = await self.client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )

            # Parse the response
            # If a Pydantic model was passed, response.parsed might be available if using SDK's high level features,
            # but usually response.text contains the JSON string.
            # Using google-genai SDK with Pydantic schema often returns a typed object object if using specific methods,
            # but standard generate_content returns an object where .text is the JSON string.
            # However, recent google-genai SDK versions allow .parsed directly if response_schema is set?
            # Let's check docs or fallback to json.loads(response.text).

            # The SDK documentation says:
            # "When you provide a Pydantic model to response_schema, the SDK automatically parses the JSON response into an instance of that model."
            # But the return type of generate_content is GenerateContentResponse.
            # Let's access .parsed if available, or .text.

            if hasattr(response, 'parsed') and response.parsed is not None:
                # If it's a Pydantic model instance, dump it to dict
                if isinstance(response.parsed, BaseModel):
                    return response.parsed.model_dump()
                return response.parsed # It might be a dict already if schema was dict

            if response.text:
                return json.loads(response.text)

            raise LLMError("Empty response from Gemini")

        except Exception as e:
            logger.error(f"Gemini structured generation failed: {e}")
            raise APIRequestError(f"Gemini API Error: {e}")

    def generate_content_sync(self, model: str, prompt: str, config: Optional[types.GenerateContentConfig] = None) -> str:
        """
        Synchronous version of generate_content.
        """
        if demo_config.is_active_stage_demo_or_any():
            raise LLMError("Refusing real Gemini call: demo mode is active for this request stage")
        if not self.client:
            raise LLMError("Gemini Client not initialized")

        try:
            logger.info(f"Calling Gemini model (Sync): {model}")

            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )

            if response.text:
                return response.text
            return ""

        except Exception as e:
            logger.error(f"Gemini sync generation failed: {e}")
            raise APIRequestError(f"Gemini API Error: {e}")

    def generate_structured_content_sync(
        self,
        model: str,
        prompt: str,
        response_schema: Union[Type[BaseModel], Dict[str, Any]],
        config: Optional[types.GenerateContentConfig] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of generate_structured_content.
        """
        if demo_config.is_active_stage_demo_or_any():
            raise LLMError("Refusing real Gemini call: demo mode is active for this request stage")
        if not self.client:
            raise LLMError("Gemini Client not initialized")

        try:
            logger.info(f"Calling Gemini structured model (Sync): {model}")

            if config is None:
                config = types.GenerateContentConfig()

            config.response_mime_type = "application/json"
            config.response_schema = self._sanitize_schema(response_schema)

            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )

            if hasattr(response, 'parsed') and response.parsed is not None:
                if isinstance(response.parsed, BaseModel):
                    return response.parsed.model_dump()
                return response.parsed

            if response.text:
                return json.loads(response.text)

            raise LLMError("Empty response from Gemini")

        except Exception as e:
            logger.error(f"Gemini structured generation (Sync) failed: {e}")
            raise APIRequestError(f"Gemini API Error: {e}")

    def _sanitize_schema(self, schema: Union[Type[BaseModel], Dict[str, Any]]) -> Union[Type[BaseModel], Dict[str, Any]]:
        """
        Sanitize schema for Gemini compatibility.
        Removes fields like 'title' and 'additionalProperties' that might cause API errors.
        """
        if isinstance(schema, dict):
            # Create a shallow copy to avoid modifying the original
            new_schema = schema.copy()

            # Remove unsupported fields
            if "title" in new_schema:
                del new_schema["title"]
            if "additionalProperties" in new_schema:
                del new_schema["additionalProperties"]

            # Recursively sanitize nested properties
            if "properties" in new_schema and isinstance(new_schema["properties"], dict):
                new_props = {}
                for key, value in new_schema["properties"].items():
                    new_props[key] = self._sanitize_schema(value)
                new_schema["properties"] = new_props

            # Recursively sanitize items (for arrays)
            if "items" in new_schema:
                new_schema["items"] = self._sanitize_schema(new_schema["items"])

            return new_schema
        return schema
