from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User
from app.schemas import CommentCreate, CommentRead, PostCreate, PostRead

router = APIRouter(tags=["Blog"])


def post_to_read(post: Post) -> dict:
    """Build the public post response without exposing ORM internals."""
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "author_username": post.author.username,
        "created_at": post.created_at,
    }


def comment_to_read(comment: Comment) -> dict:
    """Build the public comment response with its author's username."""
    return {
        "id": comment.id,
        "content": comment.content,
        "post_id": comment.post_id,
        "author_id": comment.author_id,
        "author_username": comment.author.username,
        "created_at": comment.created_at,
    }


@router.get("/posts/", response_model=list[PostRead])
def list_posts(db: Session = Depends(get_db)):
    """Return all posts, newest first."""
    posts = db.scalars(select(Post).order_by(Post.created_at.desc(), Post.id.desc())).all()
    return [post_to_read(post) for post in posts]


@router.post("/posts/", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a post owned by the authenticated user."""
    post = Post(title=payload.title.strip(), content=payload.content.strip(), author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post_to_read(post)


@router.get("/posts/{post_id}/comments/", response_model=list[CommentRead])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    """List comments for a post, returning 404 if the post does not exist."""
    if db.get(Post, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    comments = db.scalars(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc())
    ).all()
    return [comment_to_read(comment) for comment in comments]


@router.post(
    "/posts/{post_id}/comments/",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to an existing post as the authenticated user."""
    if db.get(Post, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    comment = Comment(
        content=payload.content.strip(),
        post_id=post_id,
        author_id=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_to_read(comment)
