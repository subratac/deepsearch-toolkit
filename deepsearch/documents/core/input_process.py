import datetime
import glob
import logging
import os
import pathlib
import tempfile
from threading import local
import zipfile as z
from pathlib import Path
from typing import Any, List

import urllib3
from tqdm import tqdm

from deepsearch.cps.client.api import CpsApi
from deepsearch.cps.client.components.documents import DocumentConversionResult
from .utils import batch_single_files, create_root_dir

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .common_routines import ERROR_MSG, progressbar_padding, success_message
from .convert import (
    check_status_running_tasks,
    download_converted_documents,
    get_download_url,
    send_files_for_conversion,
    send_urls_for_conversion,
)
from .create_report import report_docs, report_urls

logger = logging.getLogger(__name__)

# set up basic urls
url_user_management = "/user/v1"
url_public_apis = "/public/v4"


def process_local_input(
    api: CpsApi, cps_proj_key: str, local_file: Path, progress_bar=False, cli_use=False
) -> DocumentConversionResult:
    """
    Classify the user provided local input and take appropriate action.
    """
    if not os.path.exists(local_file):
        logger.error("Error: File not found. Check input.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            batched_files = batch_single_files(
                local_file=local_file, root_dir=tmpdir, progress_bar=progress_bar
            )
            task_ids = send_files_for_conversion(
                api=api,
                cps_proj_key=cps_proj_key,
                local_file=local_file,
                root_dir=tmpdir,
                progress_bar=progress_bar,
            )
            statuses = check_status_running_tasks(
                api=api,
                cps_proj_key=cps_proj_key,
                task_ids=task_ids,
                progress_bar=progress_bar,
            )
        if cli_use == False:
            return DocumentConversionResult(
                proj_key=cps_proj_key,
                task_ids=task_ids,
                statuses=statuses,
                source_file=local_file,
            )
        else:
            result_dir = create_root_dir()
            urls = get_download_url(
                cps_proj_key=cps_proj_key,
                task_ids=task_ids,
                api=api,
            )
            download_converted_documents(
                download_urls=urls, result_dir=result_dir, progress_bar=True
            )
            logger.info("%s\nResults: %s", success_message, os.path.abspath(result_dir))
            report_docs(
                result_dir=result_dir,
                task_ids=task_ids,
                statuses=statuses,
                local_file=local_file,
            )


def process_urls_input(
    api: CpsApi, cps_proj_key: str, urls: List[str], progress_bar=False, cli_use=False
):
    """
    Classify user provided url(s) and take appropriate action.
    """
    task_ids = send_urls_for_conversion(
        api=api, cps_proj_key=cps_proj_key, urls=urls, progress_bar=progress_bar
    )
    statuses = check_status_running_tasks(
        api=api, cps_proj_key=cps_proj_key, task_ids=task_ids, progress_bar=progress_bar
    )
    if cli_use == False:
        return DocumentConversionResult(
            proj_key=cps_proj_key,
            task_ids=task_ids,
            statuses=statuses,
            source_urls=urls,
        )
    else:
        result_dir = create_root_dir()
        urls = get_download_url(
            cps_proj_key=cps_proj_key,
            task_ids=task_ids,
            api=api,
        )
        download_converted_documents(
            download_urls=urls, result_dir=result_dir, progress_bar=True
        )
        logger.info("%s\nResults: %s", success_message, os.path.abspath(result_dir))
        report_urls(
            result_dir=result_dir,
            task_ids=task_ids,
            statuses=statuses,
            urls=urls,
        )
