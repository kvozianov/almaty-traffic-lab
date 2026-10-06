/**
 * Binary min-heap of (key, node) pairs on typed arrays. Ties break on the
 * node index so runs are identical across JavaScript engines.
 */
export class MinHeap {
  private keys: Float64Array;
  private nodes: Int32Array;
  size = 0;

  constructor(capacity: number) {
    this.keys = new Float64Array(capacity);
    this.nodes = new Int32Array(capacity);
  }

  clear(): void {
    this.size = 0;
  }

  push(key: number, node: number): void {
    if (this.size === this.keys.length) this.grow();
    let i = this.size++;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (!this.less(key, node, this.keys[parent], this.nodes[parent])) break;
      this.keys[i] = this.keys[parent];
      this.nodes[i] = this.nodes[parent];
      i = parent;
    }
    this.keys[i] = key;
    this.nodes[i] = node;
  }

  /** Removes the minimum; read it first with peekKey/peekNode. */
  pop(): void {
    const last = --this.size;
    if (last === 0) return;
    const key = this.keys[last];
    const node = this.nodes[last];
    let i = 0;
    for (;;) {
      const left = 2 * i + 1;
      if (left >= last) break;
      const right = left + 1;
      const child =
        right < last && this.less(this.keys[right], this.nodes[right], this.keys[left], this.nodes[left])
          ? right
          : left;
      if (!this.less(this.keys[child], this.nodes[child], key, node)) break;
      this.keys[i] = this.keys[child];
      this.nodes[i] = this.nodes[child];
      i = child;
    }
    this.keys[i] = key;
    this.nodes[i] = node;
  }

  peekKey(): number {
    return this.keys[0];
  }

  peekNode(): number {
    return this.nodes[0];
  }

  private less(ka: number, na: number, kb: number, nb: number): boolean {
    return ka < kb || (ka === kb && na < nb);
  }

  private grow(): void {
    const keys = new Float64Array(this.keys.length * 2);
    const nodes = new Int32Array(this.nodes.length * 2);
    keys.set(this.keys);
    nodes.set(this.nodes);
    this.keys = keys;
    this.nodes = nodes;
  }
}
