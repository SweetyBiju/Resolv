from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Wrap the error in a standard envelope
        original_data = response.data
        response.data = {
            'error': response.status_code,
            'detail': original_data
        }

    return response
