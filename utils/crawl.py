from typing import List, Set, Optional
from threading import RLock
import threading
import queue

from bs4 import BeautifulSoup
import html2text
import httpx

from llama_index.schema import Document
from llama_index.ingestion import IngestionPipeline
from llama_index.vector_stores.types import VectorStore


class Crawler:
    h2t = html2text.HTML2Text()
    h2t.ignore_links = True

    headers = {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
    }
    http_client = httpx.Client(headers=headers, verify=False)

    def __init__(
        self,
        pipeline: IngestionPipeline,
        vector_store: VectorStore,
    ) -> None:
        self.lock = RLock()
        self.crawling = False
        self.pipeline = pipeline
        self.vector_store = vector_store
        self.q = queue.Queue()

    def remove_unimportant_info(self, soup):
        """Remove unimportant tags"""

        for s in soup.select("script"):
            s.decompose()
        for s in soup.select("style"):
            s.decompose()
        for s in soup.find_all("footer", {"class": "footer"}):
            s.decompose()
        for s in soup.find_all("header", {"class": "header"}):
            s.decompose()

    def get_main_content(self, soup):
        """Get main content of page

        This is specific to HDB now.
        """
        text = ""
        for div in soup.find_all("section", {"class": "content-section"}):
            text += Crawler.h2t.handle(str(div))

        return text

    def index_document(self, soup, url):
        """Extract content and insert document to index"""

        text = self.get_main_content(soup)

        # only ingest doc if there is meaningful content
        if len(text) == 0:
            return

        # get title
        title = soup.find("title").string

        # create document with <title, url> metadata
        metadata = {
            "title": title,
            "url": url,
        }
        document = Document(text=text, metadata=metadata)

        # pipeline to transform and index document
        nodes = self.pipeline.run(documents=[document])
        self.vector_store.add(nodes)

    def process_page(self, base_url, seen_urls, crawl_url) -> None:
        """
        Process the given url. Steps include:
        1. Fetch the html file of the given url.
        2. Extract and index relevant content from html file.
        3. Extract unseen urls to process next.
        """

        response = Crawler.http_client.get(crawl_url)
        if response.status_code != 200:
            return False, ("GET failed with status %d" % (response.status_code))

        soup = BeautifulSoup(response.content, features="html.parser")

        self.remove_unimportant_info(soup)

        self.index_document(soup, crawl_url)

        child_urls = self.get_child_urls(soup, base_url, crawl_url)

        with self.lock:
            for child_url in child_urls:
                if child_url not in seen_urls:
                    seen_urls.add(child_url)
                    self.q.put(child_url)
        return True, ""

    def get_child_urls(self, soup, base_url, url) -> Set[str]:
        """Extract href links on current page that are child sites

        Example:
        Given base_url: abc.com and url: abc.com/a:
        - if href == abc.com/a/b, it is a child site
        - if href == abc.com/a, it is not a child site
        - if href == abc.com/b, it is not a child site
        """

        current_subsite_url = url[len(base_url) :]

        child_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith(current_subsite_url) or href == current_subsite_url:
                continue
            new_url = base_url + href
            child_urls.add(new_url)

        return child_urls

    def worker(self, base_url, seen_urls):
        """Get and process url from task queue"""

        while True:
            url = self.q.get()
            if url is None or url == "":
                self.q.task_done()
                break

            try:
                ok, err = self.process_page(base_url, seen_urls, url)
                if ok:
                    print("[OK] url: %s" % (url))
                else:
                    print("[ERROR] url: %s err: %s" % (url, err))
            except Exception as err:
                print("[EXCEPT] url: %s err: %s" % (url, err))
            self.q.task_done()

    def start_workers(self, base_url, seen_urls, worker_pool=1):
        threads = []
        for i in range(worker_pool):
            t = threading.Thread(
                target=self.worker, args=(base_url, seen_urls), daemon=True
            )
            t.start()
            threads.append(t)
        return threads

    def stop_workers(self, threads):
        for i in threads:
            self.q.put(None)
        for t in threads:
            t.join()

    def create_queue(self, urls):
        for url in urls:
            self.q.put(url)

    def crawl(
        self,
        base_url: str,
        seed_urls: Optional[List[str]] = None,
    ) -> None:
        """Start crawling based on given arguments

        Args:
            base_url: The root url of the website to crawl
            seed_urls: The initial urls to crawl from. If not defined, it will use the base_url.
        """

        # ensure that only 1 crawl is happening at once
        if self.crawling:
            print("an existing crawl is in progress")
            return
        self.crawling = True

        if not seed_urls or len(seed_urls) == 0:
            seed_urls = [base_url]
        seen_urls = set(seed_urls)

        # Start up your workers
        workers = self.start_workers(base_url, seen_urls, worker_pool=1)
        self.create_queue(seed_urls)

        # Blocks until all tasks are complete
        self.q.join()

        self.stop_workers(workers)
        print("visited %d urls" % (len(seen_urls)))
        self.crawling = False
