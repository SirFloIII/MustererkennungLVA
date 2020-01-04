import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image
from copy import copy
from tqdm import tqdm

class Region:

    def __init__(self, point, decomp):
        self.decomp = decomp
        self.min_idx = point
        self.max_idx = None
        self.sad_idx = set() #needn't be a point in the region!
        self.active = True
        self.points = set() #points, both inner and on the edge
        self.edge = set()   #border, belonging to the region
        self.halo = set()   #border, not (yet) part of the region
        self.add(point)

    def __repr__(self):
        return str(self.points)

    def __len__(self):
        return len(self.points)

    def __iter__(self):
        yield self.points

    def plot(self):
        assert len(self.array_shape)==2
        
        points = np.array(list(self.points)).T
        plt.scatter(points[0], points[1],
                    c="k", marker=".", s=5)

        edge = np.array(list(self.edge)).T
        plt.scatter(edge[0], edge[1],
                    c="g", marker="o", s=10)

        halo = np.array(list(self.halo)).T
        plt.scatter(halo[0], halo[1],
                    c="0.5", marker="o", s=10)
        
        plt.scatter(self.min_idx[0], self.min_idx[1],
                    c="b", marker="v", s=30)

        if self.max_idx:
            plt.scatter(self.max_idx[0], self.max_idx[1],
                        c="r", marker="^", s=30)
        
        if self.sad_idx:
            plt.scatter(self.sad_idx[0], self.sad_idx[1],
                        c="k", marker="x", s=30)
        
        plt.show()

    def add(self, point):
        assert point not in self.points
        #assert point in self.halo or not self.points
        #TODO: add an add function for sets and reactivate the assert
        
        neigh = self.decomp.get_neigh(point)
        self.points.add(point)

        new_halo = neigh.difference(self.points)

        self.halo.update(new_halo)
        self.halo.discard(point)
        
        self.edge.add(point)
        for ned in neigh.intersection(self.edge):
            if self.decomp.get_neigh(ned).issubset(self.points):
                self.edge.remove(ned)
                
        if not new_halo:
            #we found a maximum
            self.max_idx = point
            self.edge.difference_update(neigh)
            #self.passivate()
        
        
    def passivate(self):
        self.active = False
        self.halo = set()


class SlopeDecomposition:

    def __init__(self, array):
        assert array.ndim > 1
        
        self.array = array
        self.active_regions = []
        self.passive_regions = []
        
        #sort indices for increasing array value
        sorted_idx = np.unravel_index(self.array.argsort(axis=None),
                                      self.array.shape)
        
        self.unassigned_points = {tuple(idx) for idx in np.array(np.unravel_index(
                                    range(self.array.size), self.array.shape)).T}
        
        #create empty levelsets for each value that occurs
        self.levelsets = {val : set() for val in self.array[sorted_idx]}

        #then fill in the indices
        for idx in np.array(sorted_idx).T:
            self.levelsets[self.array[tuple(idx)]].add(tuple(idx))
        
        #then sort by level
        self.levelsets_sorted = sorted(self.levelsets.items(), key = lambda x:x[0])
        
        #self.decompose()
        
    def decompose(self):
        
#        debug_lvl_stop = 0
        
        for lvl, points in (self.levelsets_sorted):
            
#            print(f"""
#            Doing level: {lvl}
#            Active Regions: {len(self.active_regions)}
#            Points in Lvlset: {len(points)}   
#            """)
#            
#            if lvl >= debug_lvl_stop:
#                i = input()
#                if i == "stop":
#                    return
#                elif i.isdecimal():
#                    debug_lvl_stop = int(i)
#                elif i == "plot":
#                    self.plot()
            
            if lvl > 130:
                break
            
            self.decomposeStep(lvl, points)
            
    
    def doDecomposeStep(self):
        for lvl, points in (self.levelsets_sorted):
            self.decomposeStep(lvl, points)
            yield lvl 
    
    def decomposeStep(self, lvl, points):
  
        #first off, deal with points that can be assigned to existing regions
        while any([r.halo.intersection(points, self.unassigned_points) for r in self.active_regions]):
            for region in self.active_regions:
                active_points = points.intersection(region.halo, self.unassigned_points)
                
                while active_points and region.active:
                    point = active_points.pop()
                    
                    # das ist "dazutun"
                    region.add(point)
                    self.unassigned_points.remove(point)
                    
                    # test local connectedness around point as fast heuristic
                    local_env = self.get_cube(point).intersection(self.unassigned_points)
                    #local_env.discard(point)
                    
                    if local_env:
                    
                        if len(self.find_connected_components(local_env, local_env)) > 1:
                            # test global connectedness 
                            components = self.find_connected_components(local_env, self.unassigned_points)
                        else:
                            components = [self.unassigned_points]
                            
                        # test if colliding with another region
                        crossovers = [r for r in self.active_regions if r != region and point in r.halo]
                        if crossovers:
                            # swap halos:
                            # assign connected componets of halo union
                            # to the colliding regions
                            
                            other_region = crossovers[0]
                            components = sorted(components, key = len)
                            total_halo = region.halo.union(other_region.halo).intersection(self.unassigned_points)
                            
                            if len(components) > 0:
                                region.halo = total_halo.intersection(components[-1])
                            
                            if len(components) > 1:
                                other_region.halo = total_halo.intersection(components[-2])
                            else:
                                other_region.passivate()
                            
                        else:
                            # wenn nicht andere region:
                            #   wenn zusammenhängend:
                            #       einfach dazutun
                            #   wenn nicht zusammenhängend:
                            #       punkt dazutun
                            #       kritischer selbstzusammenstoß
                            #       iteriere über zusammenhangskomponenten.
                            #       zusammenhangskomponenten ganz im
                            #           levelset zur region vereinigen
                            #       halo wird eingeschränkt auf eine übrige
                            #           zusammenhangskomponente
                            #       (vulkan-situation)   
                                                            
                            if len(components) > 1:
                                first = True
                                for component in components:
                                    if component.issubset(points):
                                        for p in component:
                                            region.add(p)
                                            self.unassigned_points.remove(p)
                                    else:
                                        if first:
                                            first = False
                                            region.halo.intersection_update(component)
                        
                            
                    active_points = points.intersection(region.halo, self.unassigned_points)
                    
                if not region.active:
                    self.passive_regions.append(region)
                    self.active_regions.remove(region)

        #then look at remaining points and create new regions as necessary
        new_regions = []
        remaining_points = points.intersection(self.unassigned_points)
        while remaining_points:
            point = remaining_points.pop()
            region = Region(point, self)
            self.unassigned_points.remove(point)
            new_regions.append(region)

            #now fill the new region as much as possible
            active_points = remaining_points.intersection(region.halo)
            while active_points:
                for point in active_points:
                    #TODO test for special points and act accordingly
                    #can only plateau saddles happen here?
                    region.add(point)
                    self.unassigned_points.remove(point)
                active_points = remaining_points.intersection(region.halo)
                
            #and update which points are left now
            remaining_points = points.intersection(self.unassigned_points)
            
        self.active_regions += new_regions
##        if level > 115 and level < 125:
##            plot_debug(active_regions + passive_regions, a)
##            region.plot()
        
        for region in self.regions:
            region.halo.difference_update(points)
#            region.halo.intersection_update(self.unassigned_points)
    
    
    @property
    def regions(self):
        return self.active_regions + self.passive_regions

    def __len__(self):
        return len(self.regions)

    def __repr__(self):
        return "Decompostition of a "+str(self.array.shape)+\
               " "+str(self.array.dtype)+" array into "+\
               str(len(self))+" slope regions."
    
    def find_connected_components(self, small_set, big_set):
        assert small_set.issubset(big_set)
        assert len(small_set) != 0
        
        small_set_copy = copy(small_set)
        
        components = []
        while small_set_copy:
            seed = small_set_copy.pop()
            border = {seed}
            component = set()
            while border:
                point = border.pop()
                component.add(point)
                border.update(self.get_cube(point).intersection(big_set).difference(component))
            components.append(component)
            small_set_copy.difference_update(component)
        return components
    
    
    #get points with index varying at most by 1 in every dimension
    #attention when changing: same code duplicated in Region
    def get_cube(self, point):
        idx = np.array(point)
        low_corner = idx-1
        low_corner[low_corner<0] = 0
        high_corner = np.minimum(idx+1, np.array(self.array.shape)-1)
        offsets = [np.array(i)
                   for i in np.ndindex(tuple(high_corner+1-low_corner))]
        return {tuple(low_corner+o) for o in offsets}
    
    #get points that are directly adjacent along the axes
    #attention when changing: same code duplicated in Region
    def get_neigh(self, point):
        neigh = set()
        for dim, len in enumerate(self.array.shape):
            pos = point[dim]
            for k in [max(0, pos-1), pos, min(len-1, pos+1)]:
                new_idx = tuple(p if i!=dim else k for i,p in enumerate(point)) 
                neigh.add(new_idx)
        return neigh
    
    #plot 2D array in 3D projection
    def plot(self):
        assert self.array.ndim==2
        
        fig = plt.figure()
        ax = fig.gca(projection='3d')
        plt.tight_layout()
        plt.subplots_adjust(top = 1,
                            bottom = 0,
                            right = 1,
                            left = 0,
                            hspace = 0,
                            wspace = 0)

        #plot original data as wire
        x = range(self.array.shape[0])
        y = range(self.array.shape[1])
        x, y = np.meshgrid(x, y)
        ax.plot_wireframe(x.T, y.T, self.array,
                          colors="k",
                          linewidths=0.2)

        #plot colorful markers to indicate different regions
        colors = ["b", "r", "k", "c", "g", "y", "m"]
        markers = ["o", "x", "s", "+", "*"]
        for k, region in enumerate(self.regions):
            xs = [p[0] for p in region.points]
            ys = [p[1] for p in region.points]
            zs = [self.array[p] for p in region.points]
            ax.scatter(xs, ys, zs,
                       zdir="z",
                       zorder=1,
                       s=35,
                       c=colors[k%7],
                       marker=markers[k%5],
                       depthshade=False)
        plt.show()

#silly function only for debug
def plot_debug(regions, a):
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    plt.tight_layout()
    plt.subplots_adjust(top = 1,
                        bottom = 0,
                        right = 1,
                        left = 0,
                        hspace = 0,
                        wspace = 0)

    #plot original data as wire
    x = range(a.shape[0])
    y = range(a.shape[1])
    x, y = np.meshgrid(x, y)
    ax.plot_wireframe(x.T, y.T, a,
                      colors="k",
                      linewidths=0.2)

    #plot colorful markers to indicate different regions
    colors = ["b", "r", "k", "c", "g", "y", "m"]
    markers = ["o", "x", "s", "+", "*", "."]
    for k, region in enumerate(regions):
        xs = [p[0] for p in region.points]
        ys = [p[1] for p in region.points]
        zs = [a[p] for p in region.points]
        ax.scatter(xs, ys, zs,
                   zdir="z",
                   zorder=1,
                   s=10,
                   c=colors[k%7],
                   marker=markers[k%5],
                   depthshade=False)
    ax.view_init(elev=40, azim=150)
    
    plt.show()


if __name__ == "__main__":
    
    
    #dummy data for debug
    #d = np.round(10*np.random.rand(6,6)).astype(np.int)
    pic = Image.open("mediumTestImage.png")
    data = np.array(pic)[..., 1]
    d=SlopeDecomposition(data)
    #d.plot()
    #d.decompose()
    
    gen = d.doDecomposeStep()
    def step():
        try:
            gen.__next__()
        except StopIteration:
            pass

    alpha = 128
        
    colors = ((0xff, 0x9f, 0x1c, alpha),
              (0xad, 0x34, 0x3e, alpha),
              (0x06, 0x7b, 0xc2, alpha),
              (0xd9, 0x5d, 0x39, alpha),
              (0x2e, 0xc4, 0xb6, alpha),
              (0x7b, 0xa8, 0x32, alpha))
    
    
    import pygame
    
    pixelsize = 20
    bordersize = 3
    screensize = (pixelsize * data.shape[0], pixelsize * data.shape[1])
    
    
    
    pygame.init()
    screen = pygame.display.set_mode(screensize)
    pygame.display.set_caption("Border Propagation")
    clock = pygame.time.Clock()
    
    region_surface = pygame.Surface(screensize, flags = pygame.SRCALPHA)
    region_surface.set_alpha(alpha)
       
    try:
        
        done = False
        while (not done):
            # --- Main event loop
            for event in pygame.event.get(): # User did something
                if event.type == pygame.QUIT: # If user clicked close
                    done = True # Flag that we are done so we exit this loop
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
                        done = True
                    elif event.key == pygame.K_SPACE:
                        step()
                    elif event.key == pygame.K_RIGHT:
                        for _ in range(10):
                            step()
                    elif event.key == pygame.K_UP:
                        for _ in range(100):
                            step()
            
            
            # 1. Draw data
            for i in range(data.shape[0]):
                for j, v in enumerate(data[i]):
                    screen.fill((v,v,v), rect = (pixelsize*i,
                                                 pixelsize*j,
                                                 pixelsize,
                                                 pixelsize))
            
            # 2. Draw Regions
            for i, r in enumerate(d.regions):
                
                region_surface.fill((0,0,0,0))
                
                for p in r.points:
                    region_surface.fill(colors[i%len(colors)], rect = (pixelsize*p[0],
                                                               pixelsize*p[1],
                                                               pixelsize,
                                                               pixelsize))
            
                # 3. Draw Halos
                for p in r.halo:
                    region_surface.fill(colors[i%len(colors)], rect = (pixelsize*p[0] + bordersize,
                                                               pixelsize*p[1] + bordersize,
                                                               pixelsize - 2*bordersize,
                                                               pixelsize - 2*bordersize))
            
                screen.blit(region_surface, (0,0))
            
            # 4. Draw current point
            
            
            
            
            
            
            
            
            pygame.display.flip()
            
            clock.tick(60)
    
    finally:    
        pygame.quit()
    
    
