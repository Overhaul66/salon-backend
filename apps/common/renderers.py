from rest_framework.renderers import JSONRenderer

class ApiResponseRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')

        # 204 No Content must have an empty body - wrapping it in the
        # success envelope sends a 204 WITH a body, which violates the
        # HTTP spec and makes React Native reject it as a network error.
        if response is not None and response.status_code == 204:
            return super().render(None, accepted_media_type, renderer_context)

        # If it is an error response, we format as success: False
        if response and response.status_code >= 400:
            if isinstance(data, dict) and "success" in data:
                return super().render(data, accepted_media_type, renderer_context)
            
            # Extract error message if present, else fallback
            message = "An error occurred."
            errors = data
            if isinstance(data, dict) and "detail" in data:
                message = data["detail"]
                errors = {"detail": data["detail"]}
            elif isinstance(data, dict) and "non_field_errors" in data:
                message = "Validation failed."
            
            return super().render({
                "success": False,
                "message": message,
                "errors": errors
            }, accepted_media_type, renderer_context)

        # Successful response formatting
        message = "Operation successful."
        if response and hasattr(response, 'custom_message'):
            message = response.custom_message
        elif isinstance(data, dict) and "message" in data and "data" in data:
            message = data.get("message")
            data = data.get("data")
        elif isinstance(data, dict) and "message" in data and len(data) == 1:
            message = data.get("message")
            data = None

        formatted_data = {
            "success": True,
            "message": message,
            "data": data
        }
        return super().render(formatted_data, accepted_media_type, renderer_context)
